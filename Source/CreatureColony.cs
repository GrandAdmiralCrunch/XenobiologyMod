using System;
using System.Collections.Generic;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// COLONY behaviour. A host species (e.g. the Bloatfloater) carries a colony of small flyers (Crestflies) on its crown.
    /// Colonists sit on the perch, now and then fly a loop round the host, and occasionally stray down into its tendrils,
    /// where they are caught, hauled up and eaten. The host hatches replacements over time. A vessel that comes close
    /// sends the whole colony up in a swarm. If the host disappears, its colonists carry on as ordinary flyers.
    /// </summary>
    public partial class CreatureController
    {
        public CreatureController colonyHost;                       // set on a colonist while it lives on its host
        public readonly List<CreatureController> colonists = new List<CreatureController>();

        enum ColonyMode { Perch, Sortie, Return, Prey, Caught }
        ColonyMode colonyMode;
        float colonyTimer, colonyAngle, colonyAngSpeed, colonyOrbitR, colonyOrbitH, perchYaw;
        Vector3 perchLocal;                                         // (right, forward, up) metres in the host's frame
        Vector3 preyPoint;                                          // (east, north, up) metres from the host, heading-free
        Vector3 catchFrom;
        float regrowTimer, feedMsgCooldown, swarmCheck;

        public void AttachToHost(CreatureController host)
        {
            colonyHost = host;
            if (!host.colonists.Contains(this)) host.colonists.Add(this);
            var ci = host.def.colony;
            float a = Rand(0f, Mathf.PI * 2f), r = ci.perchRadius * Mathf.Sqrt(Rand(0f, 1f));
            perchLocal = new Vector3(Mathf.Cos(a) * r, Mathf.Sin(a) * r, ci.perchHeight - ci.perchDrop * r * r);
            perchYaw = Rand(0f, 360f);
            colonyMode = ColonyMode.Perch;
            colonyTimer = Rand(2f, 20f);
            SnapToPerch();
        }

        // ------------------------------------------------------------------ host side

        void TickColony(float dt)
        {
            colonists.RemoveAll(c => c == null || c.colonyHost != this);
            if (feedMsgCooldown > 0) feedMsgCooldown -= dt;
            if (colonists.Count >= def.colony.max || XenoSpawner.Instance == null) { regrowTimer = def.colony.regrowTime; return; }
            regrowTimer -= dt;
            if (regrowTimer <= 0f) { regrowTimer = def.colony.regrowTime; XenoSpawner.Instance.SpawnColonist(this); }
        }

        void OnColonistEaten(CreatureController prey)
        {
            colonists.Remove(prey);
            if (feedMsgCooldown > 0 || string.IsNullOrEmpty(def.colony.feedMessage) || FlightGlobals.ActiveVessel == null) return;
            if ((FlightGlobals.ActiveVessel.GetWorldPos3D() - WorldPos).magnitude > 600) return;
            feedMsgCooldown = 90f;
            ScreenMessages.PostScreenMessage("<color=#C8E08A>" + def.colony.feedMessage + "</color>", 5f, ScreenMessageStyle.UPPER_CENTER);
        }

        // ------------------------------------------------------------------ colonist side

        /// <summary>Drives a colonist while its host lives. Returns false (and detaches) once the host is gone.</summary>
        bool UpdateColonist(float dt)
        {
            CreatureController h = colonyHost;
            if (h == null || h.def == null || h.def.colony == null) { colonyHost = null; airborne = false; return false; }
            var ci = h.def.colony;
            colonyTimer -= dt;

            swarmCheck -= dt;
            if (swarmCheck <= 0f && (colonyMode == ColonyMode.Perch || colonyMode == ColonyMode.Return))
            {
                swarmCheck = 1f;
                if (VesselNear(h, ci.swarmDistance)) StartSortie(ci, Rand(15f, 30f), false);
            }

            switch (colonyMode)
            {
                case ColonyMode.Perch:
                    SnapToPerch();
                    if (colonyTimer <= 0f)
                    {
                        if (Rand(0f, 1f) < ci.sortieChance) StartSortie(ci, Rand(8f, 20f), true);
                        else colonyTimer = Rand(6f, 20f);
                    }
                    break;

                case ColonyMode.Sortie:
                {
                    colonyAngle += colonyAngSpeed * dt;
                    var p = new Vector3(Mathf.Cos(colonyAngle) * colonyOrbitR, Mathf.Sin(colonyAngle) * colonyOrbitR, colonyOrbitH);
                    FlyToward(h, p, false, def.speed, dt);
                    if (colonyTimer <= 0f)
                    {
                        if (preyRoll)
                        {
                            float a = Rand(0f, Mathf.PI * 2f), r = Rand(0.4f, 1f) * ci.tendrilRadius;
                            preyPoint = new Vector3(Mathf.Cos(a) * r, Mathf.Sin(a) * r, -ci.tendrilDepth * Rand(0.8f, 1.2f));
                            colonyMode = ColonyMode.Prey; colonyTimer = 25f;
                        }
                        else { colonyMode = ColonyMode.Return; colonyTimer = 20f; }
                    }
                    break;
                }

                case ColonyMode.Return:
                    if (FlyToward(h, perchLocal, true, def.speed * 0.7f, dt) < 0.4 || colonyTimer <= 0f)
                    { colonyMode = ColonyMode.Perch; colonyTimer = Rand(8f, 30f); }
                    break;

                case ColonyMode.Prey:
                    if (FlyToward(h, preyPoint, false, def.speed * 0.6f, dt) < 1.0 || colonyTimer <= 0f)
                    {
                        colonyMode = ColonyMode.Caught; colonyTimer = 7f; catchFrom = preyPoint;
                        Enter(CreatureState.Alert); speed = 0f;
                    }
                    break;

                case ColonyMode.Caught:
                {
                    // stuck on a tendril, struggling, hauled up to the digestive sacs under the bag, then gone
                    float t = 1f - Mathf.Clamp01(colonyTimer / 7f);
                    var up = new Vector3(catchFrom.x * 0.3f, catchFrom.y * 0.3f, -h.def.size * 0.28f);
                    var p = Vector3.Lerp(catchFrom, up, Mathf.SmoothStep(0f, 1f, Mathf.Clamp01((t - 0.15f) / 0.85f)));
                    SetHostPoint(h, p, false);
                    state = CreatureState.Alert; airborne = true; speed = 0f; vSpeed = 0f;
                    if (t > 0.7f) transform.localScale = Vector3.one * Mathf.Lerp(1f, 0.15f, (t - 0.7f) / 0.3f);
                    if (colonyTimer <= 0f)
                    {
                        h.OnColonistEaten(this);
                        colonyHost = null;
                        Destroy(gameObject);
                    }
                    break;
                }
            }
            return true;
        }

        bool preyRoll;

        void StartSortie(ColonyInfo ci, float duration, bool mayStray)
        {
            colonyMode = ColonyMode.Sortie; colonyTimer = duration;
            colonyOrbitR = ci.orbitRadius * Rand(0.7f, 1.3f);
            colonyOrbitH = ci.orbitHeight + Rand(-8f, 10f);
            colonyAngSpeed = (Rand(0f, 1f) < 0.5f ? -1f : 1f) * Mathf.Max(0.05f, def.speed / Mathf.Max(5f, colonyOrbitR));
            colonyAngle = Rand(0f, Mathf.PI * 2f);
            preyRoll = mayStray && Rand(0f, 1f) < ci.preyChance;
            Enter(CreatureState.Wander);
        }

        void SnapToPerch()
        {
            SetHostPoint(colonyHost, perchLocal, true);
            heading = (colonyHost.heading + perchYaw) % 360.0;
            state = CreatureState.Idle; airborne = false; speed = 0f; vSpeed = 0f;
        }

        static bool VesselNear(CreatureController h, float range)
        {
            var v = FlightGlobals.ActiveVessel;
            return v != null && v.mainBody == h.body && (v.GetWorldPos3D() - h.WorldPos).magnitude < range;
        }

        /// <summary>local: (right, forward, up) in the host's frame when hostFrame, else (east, north, up).</summary>
        void HostPoint(CreatureController h, Vector3 local, bool hostFrame, out double la, out double lo, out double al)
        {
            double e = local.x, n = local.y;
            if (hostFrame)
            {
                double hr = h.heading * Geo.Deg2Rad;
                e = local.x * Math.Cos(hr) + local.y * Math.Sin(hr);
                n = -local.x * Math.Sin(hr) + local.y * Math.Cos(hr);
            }
            la = h.lat; lo = h.lon;
            Geo.Offset(body, ref la, ref lo, n, e);
            al = h.alt + local.z;
        }

        void SetHostPoint(CreatureController h, Vector3 local, bool hostFrame)
        {
            HostPoint(h, local, hostFrame, out lat, out lon, out alt);
        }

        /// <summary>Flies toward a point on/around the host; returns the remaining distance.</summary>
        double FlyToward(CreatureController h, Vector3 local, bool hostFrame, float spd, float dt)
        {
            double la, lo, al;
            HostPoint(h, local, hostFrame, out la, out lo, out al);
            double n, e; Geo.Delta(body, lat, lon, la, lo, out n, out e);
            double u = al - alt;
            double dist = Math.Sqrt(n * n + e * e + u * u);
            state = CreatureState.Wander; airborne = true;
            if (dist < 1e-3) return 0;
            // the host drifts slowly; close the gap a bit faster than cruise speed so colonists never fall behind
            double step = Math.Min(dist, (spd + h.speed) * dt);
            double k = step / dist;
            Geo.Offset(body, ref lat, ref lon, n * k, e * k);
            alt += u * k;
            vSpeed = (float)(u * k / Math.Max(1e-3, dt));
            speed = spd;
            if (n * n + e * e > 0.01) targetHeading = heading = (Math.Atan2(e, n) * Geo.Rad2Deg + 360.0) % 360.0;
            return dist - step;
        }
    }
}
