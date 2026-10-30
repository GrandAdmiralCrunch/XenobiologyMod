using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// METAMORPHOSIS: while a vessel is watching, a larva may begin to change. It swells with gas on the sea floor,
    /// then floats up, slowly tumbling, and breaks the surface, where it becomes its next life stage (the pupa
    /// species named by `into`). That pupa starts at the waterline and keeps rising, very slowly, into the sky.
    /// </summary>
    public partial class CreatureController
    {
        bool metamorphing;
        float metaTimer, metaCheck = 5f;

        void CheckMetamorph(float dt)
        {
            var M = def.metamorph;
            if (InAction || state == CreatureState.Flee) return;
            metaCheck -= dt;
            if (metaCheck > 0f) return;
            metaCheck = 5f;
            var v = FlightGlobals.ActiveVessel;
            if (v == null || v.mainBody != body || (v.GetWorldPos3D() - WorldPos).magnitude > M.watchRange) return;
            if (rng.NextDouble() > M.chance * 5.0 / 60.0) return;
            StartMetamorph(v);
        }

        public void StartMetamorph(Vessel watcher = null)
        {
            if (def.metamorph == null || metamorphing) return;
            metamorphing = true; metaTimer = 0f; speed = 0f; targetSpeed = 0f;
            leader = null;
            Enter(CreatureState.Alert);
            if (watcher == null) watcher = FlightGlobals.ActiveVessel;
            if (!string.IsNullOrEmpty(def.metamorph.message) && watcher != null && (watcher.GetWorldPos3D() - WorldPos).magnitude < 800)
                ScreenMessages.PostScreenMessage("<color=#B8E8FF>" + def.metamorph.message + "</color>", 6f, ScreenMessageStyle.UPPER_CENTER);
        }

        void UpdateMetamorph(float dt)
        {
            var M = def.metamorph;
            metaTimer += dt;
            speed = 0f; state = CreatureState.Alert;
            float swell = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(metaTimer / Mathf.Max(0.1f, M.swellTime)));
            transform.localScale = Vector3.one * Mathf.Lerp(1f, M.swellScale, swell);
            if (metaTimer < M.swellTime) return;
            // buoyant now: rise, turning slowly, until it breaks the surface
            float lift = Mathf.Clamp01((metaTimer - M.swellTime) / 4f);
            alt += M.riseSpeed * lift * dt;
            heading = (heading + dt * 12.0) % 360.0;
            vSpeed = M.riseSpeed * lift;
            if (alt < -def.size * M.swellScale * 0.15) return;
            CreatureEffects.Splash(body, lat, lon, def.size * M.swellScale);
            if (M.intoDef != null && XenoSpawner.Instance != null)
            {
                var p = XenoSpawner.Instance.Spawn(M.intoDef, body, lat, lon);
                if (p != null) p.EmergeAtSurface(heading);
            }
            metamorphing = false;
            Destroy(gameObject);
        }

        /// <summary>A pupa that has just reached the surface: sits at the waterline, then climbs slowly through its band.</summary>
        public void EmergeAtSurface(double hdg)
        {
            heading = targetHeading = hdg;
            alt = Math.Max(groundAlt, 0.0) + 0.2;
            cruiseHeight = Rand(def.minAltitude, def.maxAltitude);
            cruiseTimer = Rand(def.cruiseChangeMin, def.cruiseChangeMax);
            Place();
        }
    }
}
