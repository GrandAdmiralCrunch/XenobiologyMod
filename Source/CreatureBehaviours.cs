using System;
using System.Collections.Generic;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Optional behaviour blocks added for ocean worlds: LIGHT (provoked by lights), LEAP (jumps clear of
    /// the water), BURST (sessile organisms that burst when touched) and sessile life in general.
    /// </summary>
    public partial class CreatureController
    {
        CreatureEffects effects;
        public CreatureEffects Effects { get { return effects; } }

        // ------------------------------------------------------------------ LIGHT: provoked by lights

        float provokedTimer;
        Vessel provoker;
        double chaseAlt;
        bool announcedProvoke;
        public bool Provoked { get { return provokedTimer > 0f && provoker != null; } }

        static readonly Dictionary<Guid, KeyValuePair<float, bool>> lightCache = new Dictionary<Guid, KeyValuePair<float, bool>>();

        /// <summary>Is this vessel showing a light? (any ModuleLight switched on, or a kerbal's helmet lamp)</summary>
        public static bool HasLightsOn(Vessel v)
        {
            if (v == null || !v.loaded) return false;
            KeyValuePair<float, bool> c;
            if (lightCache.TryGetValue(v.id, out c) && Time.time - c.Key < 1f) return c.Value;
            bool on = false;
            for (int i = 0; i < v.parts.Count && !on; i++)
            {
                Part p = v.parts[i];
                var eva = p.FindModuleImplementing<KerbalEVA>();
                if (eva != null && eva.lampOn) { on = true; break; }
                var lights = p.FindModulesImplementing<ModuleLight>();
                for (int j = 0; j < lights.Count; j++) if (lights[j].isOn) { on = true; break; }
            }
            lightCache[v.id] = new KeyValuePair<float, bool>(Time.time, on);
            return on;
        }

        bool InDarkness()
        {
            if (!def.light.darkOnly) return true;
            return alt < -def.light.darkDepth || !Geo.IsDaylight(body, lat, lon);
        }

        /// <returns>true while the creature is hunting a light (normal AI is skipped)</returns>
        bool ThinkProvoked(float dt)
        {
            var L = def.light;
            Vector3d me = WorldPos;
            if (InDarkness())
            {
                Vessel best = null; double bd = L.range;
                foreach (Vessel v in FlightGlobals.VesselsLoaded)
                {
                    if (v == null || v.mainBody != body || v.vesselType == VesselType.Debris || v.vesselType == VesselType.Flag) continue;
                    double d = (v.GetWorldPos3D() - me).magnitude;
                    if (d < bd && HasLightsOn(v)) { bd = d; best = v; }
                }
                if (best != null)
                {
                    if (!Provoked && !announcedProvoke && best == FlightGlobals.ActiveVessel)
                    {
                        announcedProvoke = true;
                        ScreenMessages.PostScreenMessage(string.IsNullOrEmpty(L.message) ? "<color=#FF7060>Something in the dark is drawn to your lights...</color>" : "<color=#E8D8A0>" + L.message + "</color>", 5f, ScreenMessageStyle.UPPER_CENTER);
                    }
                    provoker = best; provokedTimer = L.aggroTime;
                    if (state == CreatureState.Sleep) Enter(CreatureState.Alert);
                }
            }
            if (provokedTimer > 0f) provokedTimer -= dt;
            if (!Provoked) { if (provoker != null) { provoker = null; Enter(CreatureState.Wander); stateTimer = Rand(4f, 8f); } return false; }

            double dist = (provoker.GetWorldPos3D() - me).magnitude;
            double brg = Geo.Bearing(body, lat, lon, provoker.latitude, provoker.longitude);
            chaseAlt = provoker.altitude;
            targetHeading = brg;
            targetSpeed = L.chaseSpeed > 0 ? L.chaseSpeed : def.fleeSpeed;
            state = CreatureState.Approach;
            if (def.attack != null && dist < def.attack.range * 0.9) { targetSpeed = 0.5f; StartAttack(); }
            if (def.roar != null && roarCooldown <= 0f && dist < def.roar.range) { roarCooldown = def.roar.cooldown; Enter(CreatureState.Roar, def.roar.duration); }
            return true;
        }

        // ------------------------------------------------------------------ LEAP: clear of the water

        float leapCooldown;
        double leapStartAlt;
        bool leapAbove;
        bool leapGround;

        void StartLeap()
        {
            var L = def.leap;
            if (L == null || leapCooldown > 0f || InAction || def.seafloor) return;
            leapGround = def.habitat == Habitat.Ground || (def.habitat == Habitat.Flyer && !airborne);
            if (!leapGround && def.habitat != Habitat.Water && def.habitat != Habitat.Underwater) return;
            if (!leapGround && alt < -Math.Max(12.0, L.height * 3)) return;             // too deep to reach the surface
            leapStartAlt = leapGround ? groundAlt : Math.Min(alt, -def.size * 0.2);
            leapAbove = false;
            Enter(CreatureState.Leap, L.duration);
            speed = L.length / Mathf.Max(0.3f, L.duration);
            leapCooldown = L.cooldown;
        }

        void UpdateLeap(float p)
        {
            targetSpeed = def.leap.length / Mathf.Max(0.3f, def.leap.duration);
            if (p >= 1f) { Enter(CreatureState.Wander); stateTimer = Rand(2f, 5f); }
        }

        void MoveLeap(float dt)
        {
            float p = StateProgress;
            if (leapGround)
            {   // a jump on land: an arc over whatever ground passes underneath, landing on it
                double ga = leapStartAlt + (groundAlt - leapStartAlt) * p + def.leap.height * 4.0 * p * (1.0 - p);
                ga = Math.Max(ga, groundAlt);
                vSpeed = (float)((ga - alt) / Math.Max(1e-3, dt));
                alt = ga;
                if (p >= 0.98f && effects != null) effects.Fire(EmitWhen.Leap);
                return;
            }
            double h = def.leap.height + def.size * 0.3;
            double newAlt = leapStartAlt + (h - leapStartAlt) * 4.0 * p * (1.0 - p);
            vSpeed = (float)((newAlt - alt) / Math.Max(1e-3, dt));
            alt = newAlt;
            bool above = alt > 0.0;
            if (above != leapAbove)
            {
                leapAbove = above;
                CreatureEffects.Splash(body, lat, lon, def.size);
                if (effects != null) effects.Fire(EmitWhen.Leap);
            }
        }

        // ------------------------------------------------------------------ sessile life and BURST

        void ThinkSessile(float dt, bool threat, double tDist)
        {
            targetSpeed = 0f; speed = 0f;
            if (state == CreatureState.Spent)
            {
                stateTimer -= dt;
                if (stateTimer <= 0f) { SetHidden(false); Enter(CreatureState.Idle); }
                return;
            }
            if (def.burst != null && threat && tDist < def.burst.triggerRange + def.size * 0.5)
            {
                Enter(CreatureState.Burst, def.burst.duration);
                if (effects != null) effects.Fire(EmitWhen.Burst);
                if (!string.IsNullOrEmpty(def.burst.message) && threatVessel == FlightGlobals.ActiveVessel)
                    ScreenMessages.PostScreenMessage(def.burst.message, 4f, ScreenMessageStyle.UPPER_CENTER);
                // neighbours in the same patch go off too, a moment later
                var sp = XenoSpawner.Instance;
                if (sp != null)
                    foreach (var c in sp.Creatures)
                        if (c != null && c != this && c.def == def && c.state == CreatureState.Idle && (c.WorldPos - WorldPos).magnitude < def.size * 4f)
                            c.stateTimer = -1f;     // primed: bursts on its next check if still touched
                return;
            }
            bool wary = threat && tDist < Math.Max(def.fleeDistance, def.size * 2f);
            CreatureState want = wary ? CreatureState.Alert : CreatureState.Idle;
            if (state != want) Enter(want);
        }

        void UpdateBurst(float p)
        {
            targetSpeed = 0f;
            if (p >= 1f)
            {
                Enter(CreatureState.Spent);
                SetHidden(true);
                stateTimer = def.burst.regrowTime;
            }
        }
    }
}
