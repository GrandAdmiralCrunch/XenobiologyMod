using System;
using System.Collections.Generic;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>Rider input for a mounted creature, filled each frame by MountController.</summary>
    public struct RideInput
    {
        public float throttle;   // W/S  (+1 forward / dive, -1 back / pull up)
        public float turn;       // A/D  (+1 right)
        public bool run;         // Shift
        public bool jump;        // Space (pressed this frame): take off / flap
        public bool attack;      // attack key (pressed this frame)
    }

    /// <summary>
    /// One living creature. Simulated in surface coordinates (lat/lon/alt + heading) and
    /// re-projected to world space every frame. A state machine drives behaviour from the
    /// species' temperament; Flyers add take-off / glide / landing, some species sleep or
    /// attack, and rideable species hand control to a kerbal rider.
    /// </summary>
    public partial class CreatureController : MonoBehaviour
    {
        public LifeformDef def;
        public CelestialBody body;
        public double lat, lon, alt;
        public double heading;               // degrees, 0 = north
        public CreatureState state = CreatureState.Idle;
        public CreatureController leader;
        public Vector2 groupOffset;          // metres (north, east) relative to leader
        public string biome = "";
        public bool observed;
        public bool airborne;
        public float vSpeed;                 // m/s, + up
        public Vessel rider;                 // set by MountController while ridden
        public RideInput input;
        public float stamina;

        ICreatureRig rig;
        public float speed;
        float targetSpeed;
        double targetHeading;
        float stateTimer, actionTimer, actionDuration;
        float terrainTimer;
        double groundAlt;
        Vector3 groundNormal;
        float cruiseHeight, cruiseTimer;
        float depth;
        float attackCooldown;
        bool attackHit;
        float glideTimer;
        System.Random rng;
        bool placed;
        Renderer[] renderers;
        bool hidden;
        double flybyTargetLat, flybyTargetLon, flybyTargetAlt;
        bool flybyDone;
        float flybyCooldown;
        CreatureAudio audio;
        public LairInstance lair;            // set for a lair's unique resident
        public double homeLat, homeLon; public float homeRadius;   // > 0: wanders back toward home when it strays further than this
        float roarCooldown, throwCooldown;
        bool thrown;
        double HeadroomM { get { return 4.0 + def.size * 0.08; } }   // ground ray starts this far above the last ground (so roofs/overhangs don't capture it)

        public Vector3d WorldPos { get { return body.GetWorldSurfacePosition(lat, lon, alt); } }
        public bool Ridden { get { return rider != null; } }
        public double HeightAboveGround { get { return alt - Math.Max(groundAlt, body.ocean ? 0.0 : groundAlt); } }
        public float StateProgress { get { return actionDuration > 0 ? Mathf.Clamp01(actionTimer / actionDuration) : 0f; } }
        public bool IsFlyer { get { return def.habitat == Habitat.Flyer && def.flight != null; } }
        /// <summary>Swimmers float with their feet this far below the surface (the model origin is at the feet).</summary>
        double SwimLine { get { return def.waterline >= 0 ? def.waterline : def.size * 0.3; } }
        bool DeepWater(double terrain) { return def.swims && body.ocean && terrain < -SwimLine; }
        /// <summary>True while paddling at the surface (rig plays swimAnim / floatAnim).</summary>
        public bool Swimming { get { return def.swims && !airborne && state != CreatureState.Takeoff && DeepWater(groundAlt); } }

        public void Init(LifeformDef d, CelestialBody b, double la, double lo, int seed)
        {
            def = d; body = b; lat = la; lon = lo;
            rng = new System.Random(seed);
            rig = GetComponent<ICreatureRig>();
            renderers = GetComponentsInChildren<Renderer>(true);
            if (d.sounds != null) { audio = gameObject.AddComponent<CreatureAudio>(); audio.Init(d.sounds, seed); }
            if (d.emitters.Count > 0) { effects = gameObject.AddComponent<CreatureEffects>(); effects.Init(this); }
            foreach (var pl in d.plumes)
            {
                var pg = new GameObject("xeno_plume"); pg.transform.SetParent(transform, false);
                pg.AddComponent<VentPlume>().Init(this, pl);
            }
            heading = rng.NextDouble() * 360.0;
            targetHeading = heading;
            groundAlt = XenoForest.Floor(b, lat, lon, Geo.Terrain(b, lat, lon));
            { Vector3 n0; double g0 = Geo.GroundAltitude(b, lat, lon, groundAlt, out n0); if (n0 != Vector3.zero) { groundAlt = g0; groundNormal = n0; } }
            biome = Geo.Biome(b, lat, lon);
            cruiseHeight = Mathf.Lerp(d.minAltitude, d.maxAltitude, (float)rng.NextDouble());
            // gas giants: the band is tens of km deep, so start near the observer's altitude instead of anywhere in it
            if (d.habitat == Habitat.Air && !Geo.HasSurface(b) && FlightGlobals.ActiveVessel != null && FlightGlobals.ActiveVessel.mainBody == b)
                cruiseHeight = Mathf.Clamp((float)FlightGlobals.ActiveVessel.altitude + Rand(-60f - d.size * 2f, 60f + d.size * 2f), d.minAltitude, d.maxAltitude);
            depth = Mathf.Lerp(d.minAltitude, d.maxAltitude, (float)rng.NextDouble());
            alt = TargetAltitude();
            stateTimer = (float)rng.NextDouble() * 3f;
            if (IsFlyer) stamina = d.flight.flapStamina;
            if (d.sleep != null && IsSleepTime()) { state = CreatureState.Sleep; stateTimer = 9999f; }
            InitLod();
            Place();
        }

        float Rand(float a, float b) { return a + (float)rng.NextDouble() * (b - a); }
        bool TooFarFromHome()
        {
            if (homeRadius <= 0) return false;
            double n, e; Geo.Delta(body, homeLat, homeLon, lat, lon, out n, out e);
            return n * n + e * e > homeRadius * (double)homeRadius;
        }

        double TargetAltitude()
        {
            switch (def.habitat)
            {
                case Habitat.Air: return Math.Max(groundAlt, body.ocean ? 0.0 : groundAlt) + cruiseHeight;
                case Habitat.Water:
                    if (Provoked) return Math.Max(groundAlt + def.size * 0.4, Math.Min(-def.size * 0.15, chaseAlt));
                    return 0.0 - (def.waterline >= 0 ? def.waterline : def.size * 0.15);
                case Habitat.Underwater:
                    if (Provoked) return Math.Max(groundAlt + def.size * 0.4, Math.Min(-def.size * 0.3, chaseAlt));
                    if (def.seafloor) return Math.Min(groundAlt + def.minAltitude, -def.size * 0.3);
                    return Math.Max(groundAlt + def.size, -depth);
                default:
                    if (DeepWater(groundAlt)) return -SwimLine;
                    if (def.walkOnWater && body.ocean) return Math.Max(groundAlt, 0.0);
                    return groundAlt;
            }
        }

        bool HabitatAllows(double terrain)
        {
            switch (def.habitat)
            {
                case Habitat.Ground:
                case Habitat.Flyer: return airborne || !body.ocean || terrain > 0.5 || def.walkOnWater || def.swims || (def.amphibious && (def.maxWadeDepth <= 0f || terrain > -def.maxWadeDepth));
                case Habitat.Water: return body.ocean && terrain < -def.size * 0.6;
                case Habitat.Underwater: return body.ocean && terrain < (def.seafloor ? -(def.size * 0.6 + 2.0) : -(def.size * 1.5 + 1.0));
                default: return true;
            }
        }

        bool IsSleepTime()
        {
            if (def.sleep == null) return false;
            bool day = Geo.IsDaylight(body, lat, lon);
            return (def.sleep.sleepsAt == ActivityTime.Night && !day) || (def.sleep.sleepsAt == ActivityTime.Day && day);
        }

        // ------------------------------------------------------------------ threat sensing

        Vessel threatVessel;
        bool NearestThreat(out double dist, out double bearingToThreat)
        {
            dist = double.MaxValue; bearingToThreat = 0; threatVessel = null;
            Vector3d me = WorldPos;
            List<Vessel> loaded = FlightGlobals.VesselsLoaded;
            for (int i = 0; i < loaded.Count; i++)
            {
                Vessel v = loaded[i];
                if (v == null || v.mainBody != body || v.vesselType == VesselType.Debris || v.vesselType == VesselType.Flag || v.vesselType == VesselType.SpaceObject) continue;
                if (MountController.IsRiding(v)) continue;   // a kerbal on a creature's back is part of the herd, more or less
                double d = (v.GetWorldPos3D() - me).magnitude;
                if (d < dist) { dist = d; threatVessel = v; }
            }
            if (threatVessel == null) return false;
            bearingToThreat = Geo.Bearing(body, lat, lon, threatVessel.latitude, threatVessel.longitude);
            return true;
        }

        // ------------------------------------------------------------------ state helpers

        void Enter(CreatureState s, float duration = 0f)
        {
            if (state != s && XenoSettings.DebugMode) XenoLog.Dbg(def.name + " " + state + " -> " + s);
            if (audio != null && state != s) audio.OnState(s);
            state = s;
            actionTimer = 0f;
            actionDuration = duration;
            attackHit = false;
        }

        bool InAction { get { return state == CreatureState.Takeoff || state == CreatureState.Landing || state == CreatureState.Attack || state == CreatureState.Burrow || state == CreatureState.Emerge || state == CreatureState.Roar || state == CreatureState.Throw || state == CreatureState.Leap || state == CreatureState.Burst; } }

        void StartTakeoff()
        {
            if (!IsFlyer || airborne || InAction) return;
            Enter(CreatureState.Takeoff, def.flight.takeoffTime);
        }

        void StartAttack()
        {
            if (def.attack == null || attackCooldown > 0f || InAction || airborne) return;
            Enter(CreatureState.Attack, def.attack.duration);
            attackCooldown = def.attack.cooldown;
        }

        void UpdateAction(float dt)
        {
            actionTimer += dt;
            float p = StateProgress;
            switch (state)
            {
                case CreatureState.Takeoff:
                    if (p > 0.3f) { airborne = true; vSpeed = Mathf.Max(vSpeed, def.flight.climbRate * 1.4f); }
                    targetSpeed = def.flight.minSpeed * Mathf.Clamp01((p - 0.25f) * 2f);
                    if (p >= 1f)
                    {
                        Enter(CreatureState.Glide);
                        glideTimer = Rand(def.flight.minGlideTime, def.flight.maxGlideTime);
                    }
                    break;
                case CreatureState.Landing:
                    targetSpeed = 0f;
                    if (p >= 1f) { airborne = false; vSpeed = 0f; alt = DeepWater(groundAlt) ? -SwimLine : groundAlt; Enter(CreatureState.Idle); stateTimer = Rand(3f, 8f); }
                    break;
                case CreatureState.Burrow:
                    targetSpeed = 0f;
                    if (p >= 0.85f) SetHidden(true);
                    if (p >= 1f)
                    {
                        Enter(CreatureState.Underground);
                        stateTimer = Rand(def.burrow.minUnderground, def.burrow.maxUnderground);
                        targetSpeed = def.burrow.tunnelSpeed;
                    }
                    break;
                case CreatureState.Emerge:
                    targetSpeed = 0f;
                    if (p >= 0.05f) SetHidden(false);
                    if (p >= 1f) { Enter(CreatureState.Alert); stateTimer = Rand(2f, 5f); }
                    break;
                case CreatureState.Attack:
                    targetSpeed = 0f;
                    if (!attackHit && p >= def.attack.hitTime) { attackHit = true; DoAttackHit(); }
                    if (p >= 1f) { Enter(Ridden ? CreatureState.Idle : CreatureState.Alert); stateTimer = Rand(2f, 4f); }
                    break;
                case CreatureState.Roar:
                    targetSpeed = 0f;
                    if (p >= 1f) { Enter(CreatureState.Alert); stateTimer = Rand(1f, 2f); }
                    break;
                case CreatureState.Throw:
                    targetSpeed = 0f;
                    UpdateThrow(p);
                    if (p >= 1f) { EndThrow(); Enter(CreatureState.Alert); stateTimer = Rand(1f, 3f); }
                    break;
                case CreatureState.Leap:
                    UpdateLeap(p);
                    break;
                case CreatureState.Burst:
                    UpdateBurst(p);
                    break;
            }
        }

        void DoAttackHit()
        {
            Vector3d me = WorldPos;
            Vector3 up = Geo.Up(body, me);
            foreach (Vessel v in FlightGlobals.VesselsLoaded)
            {
                if (v == null || v == rider || MountController.IsRiding(v) || v.mainBody != body) continue;
                if (!v.isEVA && def.size < 10f) continue;          // only giants bother with vessels
                Vector3d d = v.GetWorldPos3D() - me;
                if (d.magnitude > def.attack.range) continue;
                if (!v.isEVA)
                {
                    // a club the size of a tree: shove the whole vessel, heavier ones less
                    float k = def.attack.knockback * Mathf.Clamp01(12f / Mathf.Max(1f, (float)v.totalMass));
                    Vector3 dirV = Vector3.ProjectOnPlane((Vector3)d, up).normalized;
                    foreach (Part p in v.parts) if (p.Rigidbody != null) p.Rigidbody.AddForce(dirV * k + up * k * 0.3f, ForceMode.VelocityChange);
                    ScreenMessages.PostScreenMessage(string.Format("<color=#FFB060>The {0} takes a swing at {1}!</color>", def.displayName, v.vesselName), 4f, ScreenMessageStyle.UPPER_CENTER);
                    continue;
                }
                Vector3 dir = Vector3.ProjectOnPlane((Vector3)d, up).normalized;
                if (dir.sqrMagnitude < 0.1f) dir = transform.right;
                Vector3 dv = dir * def.attack.knockback + up * def.attack.knockback * 0.45f;
                foreach (Part p in v.parts)
                    if (p.Rigidbody != null) p.Rigidbody.AddForce(dv, ForceMode.VelocityChange);
                ScreenMessages.PostScreenMessage(string.Format("<color=#FFB060>{0} was knocked flying by the {1}!</color>", v.vesselName, def.displayName), 4f, ScreenMessageStyle.UPPER_CENTER);
            }
            // other wildlife scatters
            var sp = XenoSpawner.Instance;
            if (sp != null)
                foreach (var c in sp.Creatures)
                    if (c != null && c != this && (c.WorldPos - me).magnitude < def.attack.range * 2.5f && !c.Ridden) c.Startle(heading);
        }

        void SetHidden(bool h)
        {
            if (hidden == h || renderers == null) return;
            hidden = h;
            ApplyVisibility();
        }

        /// <summary>Dig in (mole-style escape). Leaves a spoil heap.</summary>
        void StartBurrow(double awayHeading)
        {
            if (def.burrow == null || InAction) return;
            targetHeading = awayHeading;
            Enter(CreatureState.Burrow, def.burrow.digTime);
            SurfaceProp.SpawnMound(body, lat, lon, groundAlt, def.size * 0.35f, def.burrow.moundColor, def.burrow.moundLife);
        }

        void UpdateUnderground(float dt)
        {
            stateTimer -= dt;
            targetSpeed = def.burrow.tunnelSpeed;
            if (stateTimer <= 0f)
            {
                Enter(CreatureState.Emerge, def.burrow.emergeTime);
                SurfaceProp.SpawnMound(body, lat, lon, groundAlt, def.size * 0.35f, def.burrow.moundColor, def.burrow.moundLife);
            }
        }

        // ------------------------------------------------------------------ flyby (aerial harassers)

        void ThinkFlyby(float dt)
        {
            var f = def.flyby;
            if (flybyCooldown > 0) flybyCooldown -= dt;
            double tDist, tBearing;
            bool threat = NearestThreat(out tDist, out tBearing);
            double hd, n, e;
            switch (state)
            {
                case CreatureState.Dive:
                {
                    stateTimer -= dt;
                    Geo.Delta(body, lat, lon, flybyTargetLat, flybyTargetLon, out n, out e);
                    hd = Math.Sqrt(n * n + e * e);
                    targetHeading = Math.Atan2(e, n) * Geo.Rad2Deg;
                    targetSpeed = f.diveSpeed;
                    if (threatVessel != null) { flybyTargetLat = threatVessel.latitude; flybyTargetLon = threatVessel.longitude; flybyTargetAlt = threatVessel.altitude; }
                    if (hd < f.screechDistance) { Enter(CreatureState.Screech, f.passDuration); }
                    if (stateTimer <= -30f) { Enter(CreatureState.Wander); }   // give up after a while
                    return;
                }
                case CreatureState.Screech:
                    actionTimer += dt;
                    targetSpeed = f.diveSpeed;                                // hold course straight through the pass
                    if (actionTimer >= f.passDuration)
                    {
                        flybyDone = f.singlePass; flybyCooldown = f.cooldown;
                        Enter(CreatureState.Flee); stateTimer = 9999f;
                        targetHeading = heading + Rand(-20f, 20f);            // keep going the way it was heading
                    }
                    return;
                case CreatureState.Flee:
                    targetSpeed = f.retreatSpeed;
                    cruiseHeight = def.maxAltitude * 1.5f;
                    if (!flybyDone && flybyCooldown <= 0) Enter(CreatureState.Wander);
                    return;
            }
            // patrolling: lazy circles at cruise height, watching the ground
            stateTimer -= dt;
            if (stateTimer <= 0) { stateTimer = Rand(4f, 10f); targetHeading = heading + Rand(-90f, 90f); }
            targetHeading += dt * 10f;
            targetSpeed = def.speed;
            if (!flybyDone && flybyCooldown <= 0 && threat && tDist < f.detectRange && threatVessel != null
                && (threatVessel.isEVA || threatVessel.situation == Vessel.Situations.LANDED || threatVessel.situation == Vessel.Situations.SPLASHED))
            {
                flybyTargetLat = threatVessel.latitude; flybyTargetLon = threatVessel.longitude; flybyTargetAlt = threatVessel.altitude;
                Enter(CreatureState.Dive); stateTimer = 0f;
            }
        }

        public void ForceSleep(float seconds)
        {
            Enter(CreatureState.Sleep); stateTimer = seconds; speed = 0f; targetSpeed = 0f;
        }

        public void Startle(double fromHeading)
        {
            if (state == CreatureState.Sleep) Enter(CreatureState.Idle);
            if (IsFlyer && !airborne) { StartTakeoff(); targetHeading = fromHeading; return; }
            Enter(CreatureState.Flee); stateTimer = Rand(3f, 6f);
            targetHeading = fromHeading + Rand(-30f, 30f);
        }

        // ------------------------------------------------------------------ AI

        void Think(float dt)
        {
            double tDist, tBearing;
            bool threat = NearestThreat(out tDist, out tBearing);
            stateTimer -= dt;

            if (state == CreatureState.Underground) { UpdateUnderground(dt); return; }
            if (def.sessile) { ThinkSessile(dt, threat, tDist); return; }
            if (leapCooldown > 0f) leapCooldown -= dt;
            if (def.light != null && ThinkProvoked(dt)) return;
            if (roarCooldown <= 0f && def.roar != null && threat && tDist < def.roar.range && state != CreatureState.Sleep && !airborne)
            {   // giants with a ROAR bellow at whatever comes close, and nearby wildlife scatters
                roarCooldown = def.roar.cooldown; targetHeading = tBearing; speed = 0f; targetSpeed = 0f;
                Enter(CreatureState.Roar, def.roar.duration); ScareWildlife(def.roar.scareRadius);
                return;
            }

            // ---- sleeping: stays put; may wake when something comes close, or when sleep-time ends
            if (state == CreatureState.Sleep)
            {
                targetSpeed = 0f;
                bool wake = (stateTimer <= 0f || stateTimer > 5000f) && !IsSleepTime();   // night sleep (timer 9999) ends at dawn
                if (threat && tDist < def.sleep.wakeDistance && rng.NextDouble() < def.sleep.wakeChance * dt) wake = true;
                if (wake)
                {
                    Enter(CreatureState.Alert); stateTimer = Rand(2f, 4f);
                    if (threat) targetHeading = tBearing;
                    if (threat && def.attack != null && tDist < def.attack.range) StartAttack();
                }
                return;
            }

            // ---- airborne gliding
            if (airborne)
            {
                ThinkAir(dt, threat, tDist, tBearing);
                return;
            }

            // ---- attack anything that gets too close
            if (threat && def.attack != null && !def.attack.onlyWhenProvoked && tDist < def.attack.range && threatVessel.isEVA)
            {
                targetHeading = tBearing + 160.0;   // swing the tail round toward the intruder
                StartAttack();
                if (state == CreatureState.Attack) return;
            }

            if (threat)
            {
                switch (def.temperament)
                {
                    case Temperament.Skittish:
                        if (tDist < def.fleeDistance && def.burrow != null) { StartBurrow(tBearing + 180.0); return; }
                        if (tDist < def.fleeDistance) { if (IsFlyer) { StartTakeoff(); targetHeading = tBearing + 180; return; } Enter(CreatureState.Flee); stateTimer = Rand(3f, 6f); }
                        else if (tDist < def.alertDistance && state != CreatureState.Flee) state = CreatureState.Alert;
                        break;
                    case Temperament.Passive:
                        if (tDist < def.fleeDistance * 0.5 && def.burrow != null) { StartBurrow(tBearing + 180.0); return; }
                        if (tDist < def.fleeDistance * 0.5) { Enter(CreatureState.Flee); stateTimer = Rand(1.5f, 3f); }
                        break;
                    case Temperament.Curious:
                        if (tDist < def.alertDistance && tDist > def.fleeDistance * 0.4) state = CreatureState.Approach;
                        else if (tDist <= def.fleeDistance * 0.4) state = CreatureState.Alert;
                        break;
                    case Temperament.Territorial:
                        if (tDist < def.fleeDistance * 0.3 && def.attack == null) { Enter(CreatureState.Flee); stateTimer = Rand(2f, 4f); }
                        else if (tDist < def.alertDistance) state = tDist > Math.Max(def.fleeDistance, def.attack != null ? def.attack.range * 0.8 : 0) ? CreatureState.Approach : CreatureState.Alert;
                        break;
                }
            }
            if (state == CreatureState.Flee && stateTimer <= 0 && (!threat || tDist > def.fleeDistance)) state = CreatureState.Wander;
            if ((state == CreatureState.Alert || state == CreatureState.Approach) && (!threat || tDist > def.alertDistance * 1.2)) state = CreatureState.Wander;

            switch (state)
            {
                case CreatureState.Flee:
                    targetHeading = tBearing + 180.0 + Math.Sin(Time.time * 0.7 + lat) * 25.0;
                    targetSpeed = def.fleeSpeed;
                    if (def.leap != null && def.leap.whenFleeing && rng.NextDouble() < dt * 0.8) StartLeap();
                    break;
                case CreatureState.Alert:
                    targetHeading = tBearing;
                    targetSpeed = 0f;
                    break;
                case CreatureState.Approach:
                    targetHeading = tBearing;
                    targetSpeed = def.speed * 0.8f;
                    break;
                default:
                    if (IsFlyer && leader != null && leader != this && leader.def == def && (leader.airborne || leader.state == CreatureState.Takeoff))
                    {   // flocks: lift off a moment after the leader, heading the same way
                        if (rng.NextDouble() < dt * 2.5) { targetHeading = leader.heading; StartTakeoff(); return; }
                        targetSpeed = 0f;
                        break;
                    }
                    if (leader != null && leader != this && leader.def == def && !leader.airborne && leader.state != CreatureState.Sleep)
                    {
                        state = CreatureState.Follow;
                        FollowLeader();
                    }
                    else
                    {
                        if (state == CreatureState.Follow) state = CreatureState.Wander;
                        if (stateTimer <= 0)
                        {
                            if (def.sleep != null && (IsSleepTime() || rng.NextDouble() < def.sleep.napChance))
                            {
                                Enter(CreatureState.Sleep);
                                stateTimer = IsSleepTime() ? 9999f : Rand(def.sleep.minNap, def.sleep.maxNap);
                                return;
                            }
                            if (IsFlyer && rng.NextDouble() < def.flight.takeoffChance) { StartTakeoff(); return; }
                            if (def.leap != null && rng.NextDouble() < def.leap.chance) { targetHeading = heading + Rand(-30f, 30f); StartLeap(); if (state == CreatureState.Leap) return; }
                            bool rest = def.habitat != Habitat.Air && rng.NextDouble() < 0.45;
                            state = rest ? CreatureState.Idle : CreatureState.Wander;
                            stateTimer = rest ? Rand(2f, 7f) : Rand(4f, 12f);
                            targetHeading = heading + Rand(-70f, 70f);
                            if (TooFarFromHome()) { targetHeading = Geo.Bearing(body, lat, lon, homeLat, homeLon) + Rand(-30f, 30f); state = CreatureState.Wander; }
                            if (!def.circling && def.habitat == Habitat.Air)
                            {   // drifters: long, nearly straight legs with the wind
                                state = CreatureState.Wander; stateTimer = Rand(def.cruiseChangeMin * 0.5f, def.cruiseChangeMax * 0.5f);
                                targetHeading = heading + Rand(-25f, 25f);
                            }
                        }
                        targetSpeed = state == CreatureState.Idle ? 0f : def.speed * Rand(0.6f, 1f);
                        if (def.habitat == Habitat.Air && state == CreatureState.Wander && def.circling) targetHeading += dt * 8f;
                    }
                    break;
            }
        }

        void ThinkAir(float dt, bool threat, double tDist, double tBearing)
        {
            var f = def.flight;
            state = CreatureState.Glide;
            glideTimer -= dt;
            targetSpeed = f.cruiseSpeed;
            if (leader != null && leader != this && leader.def == def && leader.airborne && leader.state != CreatureState.Landing && (!threat || tDist > def.fleeDistance))
            {   // flock flight: hold a slot behind and beside the leader (a loose V), match its height, land when it lands
                FlyInFormation(dt);
                return;
            }
            if (leader != null && leader != this && leader.def == def && !leader.airborne && leader.state != CreatureState.Takeoff) glideTimer = Mathf.Min(glideTimer, 0f);
            if (threat && tDist < def.alertDistance) { targetHeading = tBearing + 180.0; targetSpeed = f.maxSpeed * 0.8f; glideTimer = Mathf.Max(glideTimer, 5f); }
            else if (stateTimer <= 0f) { stateTimer = Rand(3f, 8f); targetHeading = TooFarFromHome() ? Geo.Bearing(body, lat, lon, homeLat, homeLon) + Rand(-25f, 25f) : heading + Rand(-60f, 60f); }

            double h = HeightAboveGround;
            // look ahead for rising terrain
            double la = lat, lo = lon;
            Geo.Offset(body, ref la, ref lo, Math.Cos(heading * Geo.Deg2Rad) * speed * 3, Math.Sin(heading * Geo.Deg2Rad) * speed * 3);
            double ahead = Math.Max(Geo.Terrain(body, la, lo), body.ocean ? 0 : double.MinValue);
            bool wantsDown = glideTimer <= 0f;
            float targetV;
            if (ahead > alt - 10) { targetV = f.climbRate; targetHeading = heading + 40; }
            else if (!wantsDown && h < f.cruiseHeight * 0.6) targetV = f.climbRate * 0.8f;     // AI creatures may flap back up
            else targetV = wantsDown ? -f.sinkRate * 2.2f : -f.sinkRate;
            vSpeed = Mathf.MoveTowards(vSpeed, targetV, 3f * dt);
            if (wantsDown && h < 2.0) Enter(CreatureState.Landing, f.landTime);
            if (body.ocean && groundAlt < 0 && wantsDown && h < 20 && !def.swims) { glideTimer = 10f; targetHeading = heading + 90; } // don't land on water (waterfowl do)
        }

        void FlyInFormation(float dt)
        {
            var f = def.flight;
            double back = 1.5 + Math.Abs(groupOffset.x) * 0.8, side = groupOffset.y;
            double lh = leader.heading * Geo.Deg2Rad;
            double sn = -Math.Cos(lh) * back - Math.Sin(lh) * side;      // slot in north/east metres from the leader
            double se = -Math.Sin(lh) * back + Math.Cos(lh) * side;
            double ln = leader.lat, lo = leader.lon;
            Geo.Offset(body, ref ln, ref lo, sn, se);
            double n, e; Geo.Delta(body, lat, lon, ln, lo, out n, out e);
            double d = Math.Sqrt(n * n + e * e);
            targetHeading = d > 2.0 ? Math.Atan2(e, n) * Geo.Rad2Deg : leader.heading;
            // close the gap faster when behind; never stall
            double ahead = n * Math.Cos(lh) + e * Math.Sin(lh);
            targetSpeed = Mathf.Clamp(leader.speed + (float)(ahead * 0.35), f.minSpeed, f.maxSpeed);
            float wantV = Mathf.Clamp((float)((leader.alt + Math.Min(3.0, back * 0.15) - alt) * 0.8), -f.sinkRate * 2.5f, f.climbRate);
            vSpeed = Mathf.MoveTowards(vSpeed, wantV, 4f * dt);
            glideTimer = Mathf.Max(glideTimer, 1f);
            if (HeightAboveGround < 1.0 && vSpeed < 0f) vSpeed = 0f;
        }

        void FollowLeader()
        {
            double ln = leader.lat, lo = leader.lon;
            Geo.Offset(body, ref ln, ref lo, groupOffset.x, groupOffset.y);
            double n, e; Geo.Delta(body, lat, lon, ln, lo, out n, out e);
            double d = Math.Sqrt(n * n + e * e);
            if (d < 1.5) { targetHeading = leader.heading; targetSpeed = leader.speed * 0.9f; }
            else
            {
                targetHeading = Math.Atan2(e, n) * Geo.Rad2Deg;
                targetSpeed = Mathf.Min(def.fleeSpeed, (float)(leader.speed + d * 0.5));
            }
            if (leader.state == CreatureState.Flee) targetSpeed = Mathf.Max(targetSpeed, def.fleeSpeed);
        }

        // ------------------------------------------------------------------ rider control

        void Ride(float dt)
        {
            var m = def.mount;
            if (state == CreatureState.Sleep) Enter(CreatureState.Idle);
            if (input.attack) StartAttack();
            if (InAction) return;

            if (!airborne)
            {
                float fwd = input.throttle;
                targetSpeed = fwd > 0 ? (input.run ? m.runSpeed : m.walkSpeed) * fwd : fwd < 0 ? m.walkSpeed * 0.4f * fwd : 0f;
                targetHeading = heading + input.turn * m.turnRate * dt * (Mathf.Abs(speed) > 0.2f || input.turn != 0 ? 1f : 0f);
                state = Mathf.Abs(targetSpeed) > 0.1f ? (input.run ? CreatureState.Flee : CreatureState.Wander) : CreatureState.Idle;
                if (IsFlyer)
                {
                    stamina = Mathf.Min(def.flight.flapStamina, stamina + dt * 0.5f);
                    if (input.jump) StartTakeoff();
                }
                return;
            }

            // gliding
            var f = def.flight;
            state = CreatureState.Glide;
            float p = input.throttle;   // + dive, - pull up
            float tgt = p > 0 ? Mathf.Lerp(f.cruiseSpeed, f.maxSpeed, p) : Mathf.Lerp(f.cruiseSpeed, f.minSpeed * 0.7f, -p);
            targetSpeed = tgt;
            float sink = f.sinkRate * (p > 0 ? 1f + 2.5f * p : 1f - 0.6f * -p);
            if (speed < f.minSpeed) sink += (f.minSpeed - speed) * 1.2f;    // stall
            vSpeed = Mathf.MoveTowards(vSpeed, -sink, 4f * dt);
            targetHeading = heading + input.turn * m.turnRate * 0.8f * dt;
            if (input.jump && stamina >= 1f) { stamina -= 1f; vSpeed += f.flapImpulse; FlapPulse = 0.6f; }
            if (HeightAboveGround < 1.6 && vSpeed <= 0.5f) Enter(CreatureState.Landing, f.landTime);
        }

        public float FlapPulse;   // >0 while a rider-triggered flap is playing (rig uses it)

        // ------------------------------------------------------------------ motion

        void Move(float dt)
        {
            bool fleeing = state == CreatureState.Flee;
            if (Swimming && !Ridden)
            {
                float sw = def.swimSpeed > 0f ? def.swimSpeed : def.speed;
                targetSpeed = Mathf.Min(targetSpeed, sw * (fleeing ? 1.6f : 1f));
            }
            float accel = airborne ? 3f : (fleeing ? 6f : 2.5f);
            speed = Mathf.MoveTowards(speed, targetSpeed, accel * dt);
            float turnRate = airborne ? 50f : (fleeing ? 180f : (Ridden ? def.mount.turnRate : 70f));
            if (def.turnRate > 0f && !Ridden) turnRate = def.turnRate * (fleeing ? 2f : 1f);
            double dh = Mathf.DeltaAngle((float)heading, (float)targetHeading);
            if (Ridden) heading = (targetHeading + 360.0) % 360.0;
            else heading = (heading + Mathf.Clamp((float)dh, -turnRate * dt, turnRate * dt) + 360.0) % 360.0;
            if (FlapPulse > 0) FlapPulse -= dt;

            if (Mathf.Abs(speed) > 0.01f)
            {
                double step = speed * dt;
                double nl = lat, no = lon;
                Geo.Offset(body, ref nl, ref no, Math.Cos(heading * Geo.Deg2Rad) * step, Math.Sin(heading * Geo.Deg2Rad) * step);
                Vector3 nrm; bool fresh;
                double terr = ProbeTerrain(nl, no, airborne || def.habitat == Habitat.Air, out nrm, out fresh);
                if (HabitatAllows(terr))
                {
                    lat = nl; lon = no; groundAlt = terr; if (!airborne && fresh) groundNormal = nrm;
                }
                else
                {
                    if (!Ridden) targetHeading = heading + 150 + Rand(-30f, 30f);
                    speed *= Ridden ? 0f : 0.3f;
                }
            }

            probeTimer -= dt; airProbeTimer -= dt;
            terrainTimer -= dt;
            if (terrainTimer <= 0f)
            {
                terrainTimer = Lod == 0 ? 0.5f : 1.5f;
                biome = Geo.Biome(body, lat, lon);
                if (!airborne && Mathf.Abs(speed) <= 0.01f)
                {
                    Vector3 nrm;
                    double g = Geo.GroundAltitude(body, lat, lon, groundAlt, out nrm, HeadroomM);
                    if (nrm != Vector3.zero) { groundAlt = g; groundNormal = nrm; }
                }
            }
            if (attackCooldown > 0) attackCooldown -= dt;
            if (roarCooldown > 0) roarCooldown -= dt;
            if (throwCooldown > 0) throwCooldown -= dt;

            if (def.habitat == Habitat.Air)
            {
                cruiseTimer -= dt;
                bool sky = !Geo.HasSurface(body);
                if (cruiseTimer <= 0)
                {
                    cruiseTimer = Rand(def.cruiseChangeMin, def.cruiseChangeMax);
                    cruiseHeight = sky ? Mathf.Clamp(cruiseHeight + Rand(-40f - def.size, 40f + def.size), def.minAltitude, def.maxAltitude) : Rand(def.minAltitude, def.maxAltitude);
                }
                if (state == CreatureState.Flee && !sky) cruiseHeight = def.maxAltitude;
            }

            if (IsFlyer && (airborne || state == CreatureState.Landing))
            {
                double floor = Math.Max(groundAlt, body.ocean ? 0.0 : groundAlt);
                if (state == CreatureState.Landing && DeepWater(groundAlt)) floor = -SwimLine;
                if (state == CreatureState.Landing)
                {
                    // ease down onto the ground over the landing clip
                    alt = alt + (floor - alt) * Math.Min(1.0, dt * 4.0);
                    if (StateProgress > 0.5f) alt = floor;
                }
                else
                {
                    alt += vSpeed * dt;
                    if (alt < floor + 0.3)
                    {
                        alt = floor + 0.3;
                        if (vSpeed < 0) vSpeed = 0;
                        if (!Ridden && state == CreatureState.Glide && glideTimer <= 0f) Enter(CreatureState.Landing, def.flight.landTime);
                    }
                }
                return;
            }
            if (state == CreatureState.Takeoff) { alt = DeepWater(groundAlt) ? -SwimLine : groundAlt; return; }
            if (def.burrow != null && (state == CreatureState.Burrow || state == CreatureState.Underground || state == CreatureState.Emerge))
            {
                float sink = state == CreatureState.Underground ? 1f
                           : state == CreatureState.Burrow ? Mathf.SmoothStep(0f, 1f, Mathf.Clamp01((StateProgress - 0.2f) / 0.8f))
                           : 1f - Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(StateProgress / 0.45f));
                alt = groundAlt - def.burrow.depth * sink;
                return;
            }
            if (def.flyby != null && (state == CreatureState.Dive || state == CreatureState.Screech))
            {
                double floor = Math.Max(groundAlt, body.ocean ? 0.0 : groundAlt);
                double want = Math.Max(flybyTargetAlt + def.flyby.passHeight, floor + 2.0);
                double step = (state == CreatureState.Dive ? 14.0 : 4.0) * dt;
                alt += Math.Max(-step, Math.Min(step, want - alt));
                if (alt < floor + 1.5) alt = floor + 1.5;
                return;
            }
            if (def.flyby != null && state == CreatureState.Flee)
            {
                double floor = Math.Max(groundAlt, body.ocean ? 0.0 : groundAlt);
                alt = Math.Min(alt + def.flyby.climbRate * dt, floor + cruiseHeight);
                if (alt < floor + 2) alt = floor + 2;
                return;
            }

            if (state == CreatureState.Leap) { MoveLeap(dt); return; }
            double target = TargetAltitude();
            if (def.habitat == Habitat.Ground || def.habitat == Habitat.Flyer) alt = target;
            else
            {
                double bob = def.habitat == Habitat.Air ? Math.Sin(Time.time * 0.8 + lon * 50) * 0.6 * Math.Min(1.0, 3.0 / Math.Max(1f, def.size * 0.1f)) : 0;
                double na = alt + (target + bob - alt) * Math.Min(1.0, dt * (Provoked ? 2.0 : 0.8));
                if (def.maxClimbRate > 0f) na = alt + Math.Max(-def.maxClimbRate * dt, Math.Min(def.maxClimbRate * dt, na - alt));
                alt = na;
                if (def.habitat == Habitat.Air && alt < groundAlt + 1) alt = groundAlt + 1;
            }
        }

        void Place()
        {
            transform.position = WorldPos;
            Vector3 up, north, east;
            Geo.Frame(body, lat, lon, out up, out north, out east);
            Vector3 fwd = north * (float)Math.Cos(heading * Geo.Deg2Rad) + east * (float)Math.Sin(heading * Geo.Deg2Rad);
            Vector3 surfUp = up;
            bool grounded = def.habitat == Habitat.Ground || (def.habitat == Habitat.Flyer && !airborne) || (def.seafloor && !Provoked);
            if (def.walkOnWater && body.ocean && groundAlt < 0) grounded = false;     // skimming the water: stay level
            if (Swimming) grounded = false;                                          // floating: stay level
            if (def.sessile && (def.habitat == Habitat.Water || def.habitat == Habitat.Air)) grounded = false;
            if (grounded && groundNormal.sqrMagnitude > 0.5f) surfUp = Vector3.Slerp(up, groundNormal, 0.6f);
            fwd = Vector3.ProjectOnPlane(fwd, surfUp);
            Quaternion rot = Quaternion.LookRotation(fwd, surfUp);
            if (def.habitat == Habitat.Air || airborne || state == CreatureState.Leap)
            {
                float turnIn = Ridden ? input.turn * 30f : Mathf.Clamp(Mathf.DeltaAngle((float)heading, (float)targetHeading), -30f, 30f);
                float pitch = airborne ? Mathf.Clamp(-vSpeed * 3f, -25f, 25f)
                            : state == CreatureState.Leap ? Mathf.Clamp(-Mathf.Atan2(vSpeed, Mathf.Max(1f, speed)) * Mathf.Rad2Deg, -60f, 60f) : 0f;
                rot = rot * Quaternion.Euler(pitch, 0, -turnIn);
            }
            transform.rotation = placed ? Quaternion.Slerp(transform.rotation, rot, Ridden ? 0.35f : 0.25f) : rot;
            placed = true;
        }

        void Update()
        {
            if (body == null || def == null) return;
            if (FlightGlobals.ActiveVessel == null) return;
            float dt = Mathf.Min(Time.deltaTime, 0.1f);
            if (dt <= 0f) return;
            UpdateLod(dt);
            if (!TickThisFrame(dt, out dt)) return;
            if (colonyHost != null && UpdateColonist(dt))
            {
                if (rig != null) rig.Animate(dt, speed, state, airborne, actionDuration);
                return;
            }
            if (def.colony != null) TickColony(dt);
            if (metamorphing)
            {
                UpdateMetamorph(dt);
                if (rig != null) rig.Animate(dt, speed, state, airborne, actionDuration);
                return;
            }
            if (def.metamorph != null) CheckMetamorph(dt);
            if (InAction) UpdateAction(dt);
            else if (Ridden) Ride(dt);
            else if (lair != null && !def.sessile) ThinkResident(dt);
            else if (def.flyby != null) ThinkFlyby(dt);
            else Think(dt);
            Move(dt);
            input.jump = false; input.attack = false;
            if (rig != null) rig.Animate(dt, speed, state, airborne, actionDuration);
            if (effects != null) effects.Tick(this);
        }

        // Positioning happens after KSP's floating-origin / Krakensbane shifts for this frame.
        void LateUpdate()
        {
            if (body == null || def == null) return;
            if (lodHidden) return;          // invisible: nothing to place (re-placed when it comes back into view)
            Place();
        }

        public void ResetGround(double g) { groundAlt = g; alt = g; groundNormal = Vector3.zero; }

        public Transform FindChildRecursive(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            foreach (Transform t in GetComponentsInChildren<Transform>(true))
                if (t.name == name) return t;
            return null;
        }
    }
}
