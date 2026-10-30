using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Lets an EVA kerbal ride a creature that has a MOUNT node. While mounted, the kerbal stays the
    /// active vessel (so the camera, science and saving all keep working) but is made kinematic and
    /// pinned to the creature's seat transform; WASD/Space/Shift/T drive the creature instead.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Flight, false)]
    public class MountController : MonoBehaviour
    {
        public static MountController Instance { get; private set; }

        public CreatureController Mount { get; private set; }
        public Vessel Rider { get; private set; }
        Transform seat;
        KerbalEVA eva;
        Animation kerbalAnim;
        string seatedClip;
        const string LockId = "XenobiologyRide";
        GUIStyle hud;

        public static bool IsRiding(Vessel v) { return Instance != null && Instance.Rider != null && Instance.Rider == v; }

        void Awake()
        {
            Instance = this;
            GameEvents.onVesselSwitching.Add(OnSwitching);
            GameEvents.onGameSceneLoadRequested.Add(OnSceneLoad);
            GameEvents.onVesselWillDestroy.Add(OnVesselDestroy);
        }

        void OnDestroy()
        {
            GameEvents.onVesselSwitching.Remove(OnSwitching);
            GameEvents.onGameSceneLoadRequested.Remove(OnSceneLoad);
            GameEvents.onVesselWillDestroy.Remove(OnVesselDestroy);
            Dismount(false);
            if (Instance == this) Instance = null;
        }

        void OnSwitching(Vessel from, Vessel to) { if (Rider != null) Dismount(false); }
        void OnSceneLoad(GameScenes s) { if (Rider != null) Dismount(false); }
        void OnVesselDestroy(Vessel v) { if (v == Rider) { Rider = null; Dismount(false); } }

        // ------------------------------------------------------------------ mounting

        /// <summary>Closest creature this kerbal could mount right now, or a reason why not.</summary>
        public static CreatureController FindMountable(Vessel kerbal, out string reason)
        {
            reason = null;
            var sp = XenoSpawner.Instance;
            if (sp == null || kerbal == null || !kerbal.isEVA) { reason = "Only a kerbal on EVA can ride."; return null; }
            CreatureController best = null; double bestD = double.MaxValue;
            Vector3d me = kerbal.GetWorldPos3D();
            foreach (var c in sp.Creatures)
            {
                if (c == null || c.def.mount == null || c.Ridden) continue;
                double d = (c.WorldPos - me).magnitude;
                if (d <= c.def.mount.mountRange + c.def.size * 0.3 && d < bestD) { bestD = d; best = c; }
            }
            if (best == null) { reason = "Nothing rideable within reach."; return null; }
            var m = best.def.mount;
            if (m.requireAsleep && best.state != CreatureState.Sleep) { reason = "The " + best.def.displayName + " is awake. Approach one while it sleeps."; return null; }
            if (best.airborne) { reason = "It's flying."; return null; }
            ProtoCrewMember k = kerbal.GetVesselCrew().Count > 0 ? kerbal.GetVesselCrew()[0] : null;
            if (!string.IsNullOrEmpty(m.requiredTrait) && (k == null || !string.Equals(k.trait, m.requiredTrait, StringComparison.OrdinalIgnoreCase)))
            { reason = "Only a " + m.requiredTrait + " can ride a " + best.def.displayName + "."; return null; }
            return best;
        }

        public bool TryMount(Vessel kerbal)
        {
            if (Rider != null) return false;
            string why;
            CreatureController c = FindMountable(kerbal, out why);
            if (c == null) { ScreenMessages.PostScreenMessage(why, 3f, ScreenMessageStyle.UPPER_CENTER); return false; }

            seat = c.FindChildRecursive(c.def.mount.seat) ?? c.transform;
            Mount = c; Rider = kerbal;
            c.rider = kerbal;
            eva = kerbal.evaController;
            foreach (Part p in kerbal.parts)
                if (p.Rigidbody != null) { p.Rigidbody.isKinematic = true; p.Rigidbody.detectCollisions = false; }
            if (eva != null) eva.enabled = false;
            InputLockManager.SetControlLock(ControlTypes.EVA_INPUT | ControlTypes.TIMEWARP | ControlTypes.THROTTLE, LockId);
            if (TimeWarp.CurrentRate > 1f) TimeWarp.SetRate(0, true);

            kerbalAnim = kerbal.rootPart.GetComponentInChildren<Animation>();
            seatedClip = null;
            if (kerbalAnim != null)
                foreach (AnimationState st in kerbalAnim)
                    if (st.name.IndexOf("seat", StringComparison.OrdinalIgnoreCase) >= 0) { seatedClip = st.name; break; }
            if (seatedClip != null) { kerbalAnim[seatedClip].wrapMode = WrapMode.Loop; kerbalAnim.CrossFade(seatedClip, 0.3f); }

            ScreenMessages.PostScreenMessage("<color=#9CF0C8>" + kerbal.vesselName + " climbs onto the " + c.def.displayName + "!</color>", 4f, ScreenMessageStyle.UPPER_CENTER);
            if (XenoScenario.Instance != null) XenoScenario.Instance.RecordObservation(c.def, kerbal.vesselName, ScienceUtil.GetBiomedisplayName(c.body, c.biome));
            return true;
        }

        public void Dismount(bool announce = true)
        {
            if (Mount == null && Rider == null) { InputLockManager.RemoveControlLock(LockId); return; }
            CreatureController c = Mount;
            Vessel k = Rider;
            Mount = null; Rider = null;
            if (c != null) { c.rider = null; c.input = default(RideInput); }
            InputLockManager.RemoveControlLock(LockId);
            if (k == null) return;

            // step off to the side (or just let go, if airborne)
            Vector3d drop = k.GetWorldPos3D();
            Vector3 vel = Vector3.zero;
            if (c != null)
            {
                Vector3 side = c.transform.right * (c.def.size * 0.25f + 1.2f);
                if (!c.airborne)
                {
                    double la = k.mainBody.GetLatitude(drop + (Vector3d)side), lo = k.mainBody.GetLongitude(drop + (Vector3d)side);
                    double g = Geo.Terrain(k.mainBody, la, lo);
                    drop = k.mainBody.GetWorldSurfacePosition(la, lo, Math.Max(g, k.mainBody.ocean ? 0 : g) + 0.8);
                }
                else vel = c.transform.forward * c.speed + Geo.Up(c.body, c.WorldPos) * c.vSpeed;
            }
            k.SetPosition(drop);
            foreach (Part p in k.parts)
                if (p.Rigidbody != null)
                {
                    p.Rigidbody.isKinematic = false; p.Rigidbody.detectCollisions = true;
                    p.Rigidbody.velocity = vel;
                    p.Rigidbody.angularVelocity = Vector3.zero;
                }
            if (eva != null) eva.enabled = true;
            if (kerbalAnim != null && seatedClip != null) kerbalAnim.Stop(seatedClip);
            eva = null; kerbalAnim = null; seatedClip = null;
            if (announce) ScreenMessages.PostScreenMessage(k.vesselName + " hops off" + (c != null && c.airborne ? " — mid-air!" : "."), 3f, ScreenMessageStyle.UPPER_CENTER);
        }

        // ------------------------------------------------------------------ per frame

        void Update()
        {
            Vessel av = FlightGlobals.ActiveVessel;
            bool typing = GUIUtility.keyboardControl != 0;

            if (Rider == null)
            {
                if (!typing && av != null && av.isEVA && XenoSettings.MountKey != KeyCode.None && Input.GetKeyDown(XenoSettings.MountKey)
                    && !InputLockManager.IsLocked(ControlTypes.EVA_INPUT))
                    TryMount(av);
                return;
            }
            if (Mount == null || Rider == null || Rider.packed) { Dismount(false); return; }
            if (TimeWarp.CurrentRate > 1f) TimeWarp.SetRate(0, true);
            if (av != Rider) return;

            if (!typing)
            {
                if (XenoSettings.MountKey != KeyCode.None && Input.GetKeyDown(XenoSettings.MountKey)) { Dismount(); return; }
                RideInput i = Mount.input;
                i.throttle = (Input.GetKey(KeyCode.W) ? 1f : 0f) - (Input.GetKey(KeyCode.S) ? 1f : 0f);
                i.turn = (Input.GetKey(KeyCode.D) ? 1f : 0f) - (Input.GetKey(KeyCode.A) ? 1f : 0f);
                i.run = Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift);
                if (Input.GetKeyDown(KeyCode.Space)) i.jump = true;
                if (XenoSettings.RideAttackKey != KeyCode.None && Input.GetKeyDown(XenoSettings.RideAttackKey)) i.attack = true;
                Mount.input = i;
            }
            if (kerbalAnim != null && seatedClip != null && !kerbalAnim.IsPlaying(seatedClip)) kerbalAnim.CrossFade(seatedClip, 0.2f);
        }

        void FixedUpdate() { Pin(); }
        void LateUpdate() { Pin(); }

        void Pin()
        {
            if (Rider == null || Mount == null || seat == null) return;
            Vector3 pos = seat.position + seat.rotation * Mount.def.mount.seatOffset;
            Quaternion rot = Mount.transform.rotation;
            Rider.SetPosition(pos);
            Rider.SetRotation(rot);
            foreach (Part p in Rider.parts)
                if (p.Rigidbody != null) { p.Rigidbody.velocity = Vector3.zero; p.Rigidbody.angularVelocity = Vector3.zero; }
        }

        void OnGUI()
        {
            if (Rider == null || Mount == null || FlightGlobals.ActiveVessel != Rider) return;
            if (hud == null)
            {
                hud = new GUIStyle(HighLogic.Skin.box) { richText = true, alignment = TextAnchor.MiddleCenter, fontSize = 12, wordWrap = true };
            }
            var c = Mount;
            string status;
            if (c.airborne)
            {
                string pips = "";
                if (c.def.flight != null)
                    for (int i = 0; i < c.def.flight.flapStamina; i++) pips += i < Mathf.FloorToInt(c.stamina) ? "●" : "○";
                status = string.Format("<b>{0}</b> — gliding  {1:F0} m/s  {2:F0} m above ground  {3:+0.0;-0.0} m/s vertical   flaps {4}\n" +
                                       "W dive · S pull up · A/D bank · Space flap · {5} dismount (you will fall!)",
                    c.def.displayName, c.speed, c.HeightAboveGround, c.vSpeed, pips, XenoSettings.MountKey);
            }
            else
            {
                status = string.Format("<b>{0}</b> — {1:F1} m/s\nW/S move · A/D turn · Shift run{2}{3} · {4} dismount",
                    c.def.displayName, c.speed,
                    c.IsFlyer ? " · Space take off" : "",
                    c.def.attack != null ? " · " + XenoSettings.RideAttackKey + " attack" : "",
                    XenoSettings.MountKey);
            }
            float w = 640, h = 46;
            GUI.Box(new Rect((Screen.width - w) / 2, Screen.height - h - 90, w, h), status, hud);
        }
    }
}
