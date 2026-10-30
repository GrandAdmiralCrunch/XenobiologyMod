using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Keeps Parallax Continued's terrain scatters (kelp, grass, rocks, trees) off a lair site, by adding a
    /// Parallax "PQSMod_MapDecalVertexRemoveScatter" to the body's PQS at runtime. This is the mod Parallax itself uses
    /// to keep trees off the KSC; it normally comes from a Kopernicus config, but lair sites are chosen per save, so
    /// here it is built in code. No hard dependency: without Parallax this does nothing.
    /// The mask texture is white (scatters allowed) with a black disc (blocked), as in Parallax's kscMask.
    /// </summary>
    public static class ParallaxCompat
    {
        static Type decalType;
        static bool looked;
        static readonly HashSet<string> done = new HashSet<string>();

        static Type DecalType()
        {
            if (looked) return decalType;
            looked = true;
            foreach (var la in AssemblyLoader.loadedAssemblies)
            {
                if (la.assembly == null) continue;
                var t = la.assembly.GetType("Parallax.PQS_Mods.PQSMod_MapDecalVertexRemoveScatter", false);
                if (t != null) { decalType = t; break; }
            }
            if (decalType != null) XenoLog.Info("Parallax found: lairs can clear terrain scatters");
            return decalType;
        }

        /// <summary>Every scatter name Parallax has for this body (kelp, grass, trees...).</summary>
        static List<string> ScatterNames(CelestialBody b, Type decal)
        {
            var names = new List<string>();
            try
            {
                Type cl = decal.Assembly.GetType("Parallax.ConfigLoader");
                var dict = cl.GetField("parallaxScatterBodies", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static).GetValue(null) as IDictionary;
                if (dict == null) return names;
                foreach (DictionaryEntry e in dict)
                {
                    if ((e.Key as string) != b.name) continue;
                    object body = e.Value;
                    foreach (string field in new[] { "fastScatters", "scatters" })
                    {
                        var f = body.GetType().GetField(field, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                        var coll = f != null ? f.GetValue(body) : null;
                        IEnumerable items = coll is IDictionary ? (IEnumerable)((IDictionary)coll).Values : coll as IEnumerable;
                        if (items == null) continue;
                        foreach (object s in items)
                        {
                            if (s == null) continue;
                            var nf = s.GetType().GetField("scatterName", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                            string n = nf != null ? nf.GetValue(s) as string : null;
                            if (!string.IsNullOrEmpty(n) && !names.Contains(n)) names.Add(n);
                        }
                    }
                }
            }
            catch (Exception ex) { XenoLog.Warn("Parallax scatter list: " + ex.Message); }
            return names;
        }

        static Texture2D Mask(float discFraction)
        {
            const int N = 256;
            var tex = new Texture2D(N, N, TextureFormat.RGBA32, false);
            tex.wrapMode = TextureWrapMode.Clamp;
            var px = new Color32[N * N];
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                {
                    float dx = (x + 0.5f) / N * 2f - 1f, dy = (y + 0.5f) / N * 2f - 1f;
                    float r = Mathf.Max(Mathf.Abs(dx), Mathf.Abs(dy));           // a square: blocked out to the decal's edge
                    float k = Mathf.Clamp01((r - discFraction) / 0.1f);         // soft edge: thinning kelp at the rim
                    byte c = (byte)(k * 255);
                    px[y * N + x] = new Color32(c, c, c, 255);
                }
            tex.SetPixels32(px); tex.Apply(false, false);
            return tex;
        }

        /// <summary>Clear scatters within radiusM of (lat, lon). Returns true if a mask was added.</summary>
        public static bool ClearAround(CelestialBody b, string id, double lat, double lon, double radiusM, Vessel v)
        {
            if (b == null || b.pqsController == null || !done.Add(b.name + "/" + id)) return false;
            Type t = DecalType();
            if (t == null) return false;
            try
            {
                PQS pqs = b.pqsController;
                var names = ScatterNames(b, t);
                if (names.Count == 0) { XenoLog.Info("Parallax: no scatters on " + b.name); return false; }
                var go = new GameObject("XenoScatterMask_" + id);
                go.transform.SetParent(pqs.transform, false);
                var mod = (PQSMod)go.AddComponent(t);
                const BindingFlags BF = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;
                double decalR = radiusM / 0.88;                                 // the black square covers 88 % of the decal
                t.GetField("blockedScatters", BF).SetValue(mod, names);
                t.GetField("radius", BF).SetValue(mod, decalR);
                t.GetField("position", BF).SetValue(mod, (Vector3)b.GetRelSurfaceNVector(lat, lon));
                t.GetField("angle", BF).SetValue(mod, 0f);
                t.GetField("colorMap", BF).SetValue(mod, Mask(0.88f));
                mod.sphere = pqs;
                mod.modEnabled = true;
                mod.order = 99998;
                mod.OnSetup();
                // append it to the PQS mod list so OnQuadPreBuild registers the quads it covers
                var fMods = typeof(PQS).GetField("mods", BF); var fCount = typeof(PQS).GetField("modCount", BF);
                var list = new List<PQSMod>((fMods.GetValue(pqs) as PQSMod[]) ?? new PQSMod[0]);
                list.Add(mod);
                fMods.SetValue(pqs, list.ToArray());
                fCount.SetValue(pqs, list.Count);
                XenoLog.Info(string.Format("Parallax: cleared {0} scatter type(s) within {1:F0} m of {2} ({3})", names.Count, radiusM, id, string.Join(", ", names.ToArray())));
                // quads already built near the site won't have seen the mask: rebuild them if we're close
                if (v != null)
                {
                    Vector3d site = b.GetWorldSurfacePosition(lat, lon, 0);
                    if ((v.GetWorldPos3D() - site).magnitude < 30000) pqs.RebuildSphere();
                }
                return true;
            }
            catch (Exception ex) { XenoLog.Warn("Could not add a Parallax scatter mask: " + ex.Message); return false; }
        }
    }
}
