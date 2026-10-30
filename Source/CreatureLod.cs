using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Xenobiology
{
    /// <summary>
    /// Distance-based level of detail for creatures. Every half second each creature measures its distance to the
    /// camera and picks a level:
    ///   0 near   - full simulation, shadows (if the creature is big enough), full-quality skinning;
    ///   1 mid    - no shadows, 2-bone skinning, ground probe 5x a second instead of every frame;
    ///   2 far    - also 1-bone skinning, and the AI/motion runs every 3rd frame (accumulating the time);
    ///   3 culled - too far to see: renderers and animation off, AI every 8th frame, no per-frame placement.
    /// Distances scale with the creature's size, so a 40 m giant stays visible kilometres away and a butterfly
    /// disappears at a few hundred metres, where it would be a pixel anyway.
    /// </summary>
    public partial class CreatureController
    {
        public int Lod { get; private set; }
        float lodTimer;
        int lodSlot;
        float pendingDt;
        bool lodHidden;
        bool lodReady;
        SkinnedMeshRenderer[] lodSkins;
        Animation[] lodAnims;
        float probeTimer, airProbeTimer, airTerr = float.NaN;
        static int slotCounter;

        void InitLod()
        {
            lodSkins = GetComponentsInChildren<SkinnedMeshRenderer>(true);
            lodAnims = GetComponentsInChildren<Animation>(true);
            lodSlot = (slotCounter++) & 7;
            lodTimer = (lodSlot & 3) * 0.12f;           // spread the distance checks over a few frames
            Lod = -1;
            lodReady = true;
            SetLod(0);
        }

        float LodNear { get { return XenoSettings.LodNearDistance + def.size * 10f; } }
        float LodFar { get { return XenoSettings.LodFarDistance + def.size * 25f; } }
        float LodCull { get { return XenoSettings.LodCullDistance + def.size * XenoSettings.LodCullPerMetre; } }

        /// <summary>Re-evaluates the LOD twice a second.</summary>
        void UpdateLod(float dt)
        {
            if (!lodReady) InitLod();
            lodTimer -= dt;
            if (lodTimer > 0f) return;
            lodTimer = 0.5f;
            int want;
            if (Ridden || !XenoSettings.LodEnabled) want = 0;
            else
            {
                Vector3d cam = CameraPos();
                double d = (WorldPos - cam).magnitude;
                want = d > LodCull ? 3 : d > LodFar ? 2 : d > LodNear ? 1 : 0;
                if (want == 3 && (InAction || state == CreatureState.Flee) && d < LodCull * 1.5) want = 2;   // don't vanish mid-charge
            }
            if (want != Lod) SetLod(want);
        }

        static Vector3d CameraPos()
        {
            if (FlightCamera.fetch != null && FlightCamera.fetch.mainCamera != null) return FlightCamera.fetch.mainCamera.transform.position;
            return FlightGlobals.ActiveVessel != null ? FlightGlobals.ActiveVessel.GetWorldPos3D() : Vector3d.zero;
        }

        void SetLod(int l)
        {
            int was = Lod;
            Lod = l;
            bool shadows = l == 0 && XenoSettings.CreatureShadows && def.size >= XenoSettings.ShadowMinSize;
            if (renderers != null)
                foreach (var r in renderers)
                {
                    if (r == null) continue;
                    r.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
                }
            if (lodSkins != null)
                foreach (var s in lodSkins)
                    if (s != null) s.quality = l == 0 ? SkinQuality.Auto : l == 1 ? SkinQuality.Bone2 : SkinQuality.Bone1;
            bool cull = l == 3;
            if (cull != lodHidden)
            {
                lodHidden = cull;
                ApplyVisibility();
                if (lodAnims != null) foreach (var a in lodAnims) if (a != null) a.enabled = !cull;
                if (!cull && was == 3) Place();
            }
            if (was >= 2 && l < 2) pendingDt = 0f;
        }

        void ApplyVisibility()
        {
            if (renderers == null) return;
            bool show = !hidden && !lodHidden;
            foreach (var r in renderers) if (r != null) r.enabled = show;
        }

        /// <summary>Far creatures think and move every few frames, with the skipped time added up.</summary>
        bool TickThisFrame(float dt, out float tickDt)
        {
            tickDt = dt;
            if (Lod < 2) return true;
            int period = Lod == 2 ? 3 : 8;
            pendingDt += dt;
            if (((Time.frameCount + lodSlot) % period) != 0) return false;
            tickDt = Mathf.Min(pendingDt, 0.5f);
            pendingDt = 0f;
            return true;
        }

        /// <summary>Ground height at a new position. Near creatures raycast the terrain colliders every frame (feet on the
        /// ground); further away the probe runs 5x a second, and flying/air species sample the PQS terrain 5x a second
        /// (a PQS height query runs every terrain mod of the planet and is the most expensive call a creature makes).</summary>
        double ProbeTerrain(double nl, double no, bool flying, out Vector3 nrm, out bool fresh)
        {
            nrm = Vector3.zero; fresh = false;
            if (flying)
            {
                if (airProbeTimer <= 0f || float.IsNaN(airTerr))
                {
                    airTerr = (float)XenoForest.Floor(body, nl, no, Geo.Terrain(body, nl, no)); airProbeTimer = Lod == 0 ? 0.1f : 0.25f; fresh = true;
                }
                return airTerr;
            }
            if (Lod == 0 && def.habitat != Habitat.Air || probeTimer <= 0f)
            {
                probeTimer = Lod <= 1 ? 0.2f : 0.5f;
                fresh = true;
                double terr = Geo.GroundAltitude(body, nl, no, groundAlt, out nrm, HeadroomM);
                if (nrm == Vector3.zero) terr = XenoForest.Floor(body, nl, no, Geo.Terrain(body, nl, no));   // no collider loaded here
                return terr;
            }
            return groundAlt;
        }
    }
}
