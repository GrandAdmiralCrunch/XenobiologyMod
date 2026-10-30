using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Behaviour for a lair's unique resident (e.g. the Kerbin Cyclops): keeps to a home range
    /// around its lair, walks in through the entrance at dusk and sleeps in the den, comes back out
    /// at dawn, roars at intruders, hurls boulders at anything in throwing range and smashes
    /// whatever gets underfoot.
    /// </summary>
    public partial class CreatureController
    {
        Vessel throwTarget;
        GameObject heldRock;
        int routeStage;            // 0 = head to the entrance, 1 = through the tunnel to the den / out to the pen

        double DistTo(double la, double lo)
        {
            double n, e; Geo.Delta(body, lat, lon, la, lo, out n, out e);
            return Math.Sqrt(n * n + e * e);
        }

        double BearingTo(double la, double lo) { return Geo.Bearing(body, lat, lon, la, lo); }

        bool WalkTo(double la, double lo, float spd, double arrive)
        {
            double d = DistTo(la, lo);
            if (d <= arrive) { targetSpeed = 0f; return true; }
            targetHeading = BearingTo(la, lo);
            targetSpeed = d < arrive * 3 ? spd * 0.6f : spd;
            if (state != CreatureState.Wander) state = CreatureState.Wander;
            return false;
        }

        void ThinkResident(float dt)
        {
            var L = lair;
            double tDist, tBearing;
            bool threat = NearestThreat(out tDist, out tBearing);
            stateTimer -= dt;
            bool night = IsSleepTime();
            bool inside = L.Inside(lat, lon);

            // ---- asleep in the den
            if (state == CreatureState.Sleep)
            {
                targetSpeed = 0f;
                bool roused = threat && def.sleep != null && tDist < def.sleep.wakeDistance && rng.NextDouble() < def.sleep.wakeChance * dt;
                if (!night || roused)
                {
                    Enter(CreatureState.Alert); stateTimer = Rand(2f, 4f);
                    routeStage = 0;
                    if (!night) L.SetDoor(true);
                    if (roused) targetHeading = tBearing;
                }
                return;
            }

            // ---- intruders
            float notice = def.roar != null ? Mathf.Max(def.roar.range, def.alertDistance) : def.alertDistance;
            if (threat && tDist < notice && threatVessel != null && (!inside || tDist < 60))
            {
                targetHeading = tBearing;
                double tLat = threatVessel.latitude, tLon = threatVessel.longitude;
                double intruderFromHome = L.DistFromEntrance(tLat, tLon);

                if (def.roar != null && roarCooldown <= 0f)
                {
                    Enter(CreatureState.Roar, def.roar.duration); roarCooldown = def.roar.cooldown;
                    ScareWildlife(def.roar.scareRadius);
                    if (tDist < 1500) ScreenMessages.PostScreenMessage("<color=#FF9050>A bellow shakes the hills...</color>", 3f, ScreenMessageStyle.UPPER_CENTER);
                    return;
                }
                if (def.attack != null && tDist < def.attack.range)
                {
                    if (Mathf.Abs(Mathf.DeltaAngle((float)heading, (float)tBearing)) < 40f) StartAttack();
                    if (state == CreatureState.Attack) return;
                }
                if (def.throwing != null && throwCooldown <= 0f && tDist >= def.throwing.minRange && tDist <= def.throwing.maxRange
                    && Mathf.Abs(Mathf.DeltaAngle((float)heading, (float)tBearing)) < 30f)
                {
                    StartThrow(threatVessel);
                    return;
                }
                bool close = def.attack != null && tDist < def.attack.range * 0.8;
                if (!close && intruderFromHome < L.def.leash && L.DistFromEntrance(lat, lon) < L.def.leash)
                {
                    state = CreatureState.Approach;
                    targetSpeed = tDist < 120 ? def.fleeSpeed : def.speed;   // charges the last stretch
                }
                else { state = CreatureState.Alert; targetSpeed = 0f; }
                return;
            }

            // ---- dusk: walk home and bed down in the den
            if (night)
            {
                if (!inside && routeStage == 0)
                {
                    if (WalkTo(L.entranceLat, L.entranceLon, def.speed, 10)) routeStage = 1;
                    return;
                }
                routeStage = 1;
                if (WalkTo(L.denLat, L.denLon, def.speed * 0.8f, 5))
                {
                    targetHeading = BearingTo(L.entranceLat, L.entranceLon);
                    if (Mathf.Abs(Mathf.DeltaAngle((float)heading, (float)targetHeading)) < 15f)
                    {
                        Enter(CreatureState.Sleep); stateTimer = 9999f;
                        L.SetDoor(false);
                    }
                    else state = CreatureState.Idle;
                }
                return;
            }

            // ---- day: out of the cave, minding the flock within the home range
            L.SetDoor(true);
            if (inside)
            {
                WalkTo(L.entranceLat, L.entranceLon, def.speed * 0.8f, 6);
                routeStage = 0;
                return;
            }
            if (state == CreatureState.Alert && stateTimer > 0f) { targetSpeed = 0f; return; }
            if (L.DistFromEntrance(lat, lon) > L.def.leash)
            {
                WalkTo(L.penLat, L.penLon, def.speed, 20);
                stateTimer = Rand(4f, 8f);
                return;
            }
            if (stateTimer <= 0f || state == CreatureState.Alert || state == CreatureState.Approach)
            {
                bool rest = rng.NextDouble() < 0.4;
                state = rest ? CreatureState.Idle : CreatureState.Wander;
                stateTimer = rest ? Rand(6f, 16f) : Rand(8f, 20f);
                if (!rest)
                {
                    // stroll toward a random spot around the pen
                    double la = L.penLat, lo = L.penLon;
                    float r = L.def.leash * 0.55f * Mathf.Sqrt((float)rng.NextDouble());
                    float a = Rand(0f, Mathf.PI * 2f);
                    Geo.Offset(body, ref la, ref lo, Math.Cos(a) * r, Math.Sin(a) * r);
                    targetHeading = BearingTo(la, lo);
                }
            }
            targetSpeed = state == CreatureState.Idle ? 0f : def.speed * 0.7f;
        }

        void ScareWildlife(float radius)
        {
            var sp = XenoSpawner.Instance;
            if (sp == null) return;
            Vector3d me = WorldPos;
            foreach (var c in sp.Creatures)
                if (c != null && c != this && !c.Ridden && c.lair == null && (c.WorldPos - me).magnitude < radius)
                    c.Startle(Geo.Bearing(body, lat, lon, c.lat, c.lon));
        }

        // ------------------------------------------------------------------ throwing

        void StartThrow(Vessel target)
        {
            var t = def.throwing;
            throwTarget = target;
            Enter(CreatureState.Throw, t.duration);
            throwCooldown = t.cooldown;
            thrown = false;
            if (heldRock != null) Destroy(heldRock);
            Transform hand = FindChildRecursive(t.hand);
            if (hand != null)
            {
                heldRock = Boulder.MakeRock("XenoHeldRock", t.radius, t.color, rng.Next());
                heldRock.transform.SetParent(hand, false);
                heldRock.transform.localPosition = t.releaseOffset;
                heldRock.SetActive(false);    // appears as the hand scoops it off the ground
            }
        }

        void UpdateThrow(float p)
        {
            var t = def.throwing;
            if (throwTarget != null) targetHeading = Geo.Bearing(body, lat, lon, throwTarget.latitude, throwTarget.longitude);
            if (heldRock != null && !heldRock.activeSelf && p > t.releaseTime * 0.35f)
            {
                heldRock.SetActive(true);
                // keep the world-space size constant whatever the bone scale is
                Vector3 ls = heldRock.transform.lossyScale;
                if (ls.x > 1e-4f) heldRock.transform.localScale = heldRock.transform.localScale * (t.radius * 2f / ls.x);
            }
            if (thrown || p < t.releaseTime) return;
            thrown = true;
            Vector3d from = heldRock != null ? (Vector3d)heldRock.transform.position : WorldPos + (Vector3d)(transform.up * def.size * 0.85f);
            if (heldRock != null) { Destroy(heldRock); heldRock = null; }
            if (throwTarget == null || throwTarget.mainBody != body) return;
            if (audio != null && def.sounds != null) audio.Play(def.sounds.throwSound);
            Vector3d aim = throwTarget.CoM;
            Vector3 vel;
            if (!Boulder.Solve(body, from, aim, throwTarget.srf_velocity * t.lead, t.launchSpeed, out vel)) return;
            // a little human (cyclopean?) error
            Vector3 up = Geo.Up(body, from);
            Vector3 side = Vector3.Cross(up, vel).normalized;
            float flight = (float)((aim - from).magnitude / Math.Max(1.0, vel.magnitude));
            vel += side * Rand(-t.spread, t.spread) / Mathf.Max(1f, flight);
            Boulder.Launch(body, from, vel, t, def.sounds, this);
        }

        void EndThrow()
        {
            if (heldRock != null) { Destroy(heldRock); heldRock = null; }
            throwTarget = null;
        }

        void OnDestroy()
        {
            if (heldRock != null) Destroy(heldRock);
        }
    }
}
