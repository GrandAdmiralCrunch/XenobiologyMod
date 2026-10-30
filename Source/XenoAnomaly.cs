using System.Collections.Generic;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// A surface anomaly marker for a lair or landmark. KSP keeps its anomalies (the monoliths, the face...)
    /// in CelestialBody.pqsSurfaceObjects; KerbNet's anomaly scan reads that list and the object's position,
    /// and so do mods such as SCANsat. Each marker is an empty object glued to the planet at the site.
    /// </summary>
    public class XenoAnomaly : PQSSurfaceObject
    {
        public string objectName, displayName;
        public CelestialBody body;
        public double lat, lon, alt;

        public override string SurfaceObjectName { get { return objectName; } }
        public override string DisplaySurfaceObjectName { get { return displayName; } }
        public override Vector3d PlanetRelativePosition { get { return body.GetRelSurfaceNVector(lat, lon) * (body.Radius + alt); } }

        static readonly Dictionary<string, XenoAnomaly> all = new Dictionary<string, XenoAnomaly>();

        public static void Register(CelestialBody b, string id, string display, double lat, double lon)
        {
            if (b == null) return;
            try
            {
                XenoAnomaly a;
                if (!all.TryGetValue(id, out a) || a == null)
                {
                    var go = new GameObject(id);
                    DontDestroyOnLoad(go);
                    a = go.AddComponent<XenoAnomaly>();
                    a.objectName = id;
                    all[id] = a;
                }
                a.displayName = display; a.body = b; a.lat = lat; a.lon = lon;
                a.alt = Geo.Terrain(b, lat, lon) + 2.0;
                a.transform.SetParent(null, false);
                a.transform.position = b.GetWorldSurfacePosition(lat, lon, a.alt);
                a.transform.SetParent(b.bodyTransform != null ? b.bodyTransform : b.transform, true);

                var list = new List<PQSSurfaceObject>();
                if (b.pqsSurfaceObjects != null)
                    foreach (var o in b.pqsSurfaceObjects) if (o != null && o != a && o.SurfaceObjectName != id) list.Add(o);
                list.Add(a);
                b.pqsSurfaceObjects = list.ToArray();
            }
            catch (System.Exception e) { XenoLog.Warn("Could not register anomaly " + id + ": " + e.Message); }
        }
    }
}
