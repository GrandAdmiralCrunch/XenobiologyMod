using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// Lets an EVA kerbal dive. Stock kerbals bob on the surface like corks, which makes reefs and wrecks unreachable.
    /// While swimming, holding the jetpack-down key (Left Ctrl by default) dives; underwater the kerbal is neutrally
    /// buoyant: jetpack-down sinks, jetpack-up (Left Shift) rises, neither holds the depth. The normal swim controls
    /// still move the kerbal around. Surfacing (or leaving the water) restores stock buoyancy.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Flight, false)]
    public class XenoDiving : MonoBehaviour
    {
        const float VerticalSpeed = 1.6f;      // m/s up or down
        const float Gain = 3.0f;               // how hard the vertical speed is held (1/s)
        const float MaxAccel = 25f;            // m/s^2, enough to overpower any buoyancy the game still applies
        const float SwimBoost = 1.6f;          // underwater swimming is a bit faster than paddling on the surface

        Part diver;
        float savedBuoyancy, savedSwimSpeed;
        KerbalEVA diverEva;
        static bool hintShown;

        bool Diving { get { return diver != null; } }

        void FixedUpdate()
        {
            Vessel v = FlightGlobals.ActiveVessel;
            if (!XenoSettings.KerbalDiving || v == null || !v.isEVA || v.mainBody == null || !v.mainBody.ocean || v.rootPart == null || v.rootPart.rb == null)
            {
                EndDive(); return;
            }
            Part p = v.rootPart;
            if (Diving && p != diver) EndDive();
            bool inWater = v.altitude < 0.3 && (p.WaterContact || v.altitude < -0.6);
            if (!inWater) { EndDive(); return; }

            bool canInput = !InputLockManager.IsLocked(ControlTypes.EVA_INPUT) && !FlightDriver.Pause && !MapView.MapIsEnabled;
            bool down = canInput && GameSettings.EVA_Pack_down.GetKey();
            bool up = canInput && GameSettings.EVA_Pack_up.GetKey();

            if (!Diving)
            {
                if (!hintShown && NearUnderwaterLair(v))
                {
                    hintShown = true;
                    ScreenMessages.PostScreenMessage(string.Format("<color=#9FE0FF>Hold [{0}] to dive, [{1}] to rise</color>",
                        GameSettings.EVA_Pack_down.primary, GameSettings.EVA_Pack_up.primary), 8f, ScreenMessageStyle.UPPER_CENTER);
                }
                if (!down) return;
                BeginDive(p);
            }
            else if (v.altitude > -0.4 && !down)
            {   // back at the surface: stock buoyancy takes over again
                EndDive(); return;
            }

            Rigidbody rb = p.rb;
            Vector3 upv = (Vector3)(v.GetWorldPos3D() - v.mainBody.position).normalized;
            // cancel gravity: neutral buoyancy (the part's own buoyancy is switched off while diving)
            Vector3 g = (Vector3)FlightGlobals.getGeeForceAtPosition(rb.worldCenterOfMass);
            rb.AddForce(-g, ForceMode.Acceleration);
            // hold the asked-for vertical speed
            float target = up ? VerticalSpeed : down ? -VerticalSpeed : 0f;
            if (up && v.altitude > -1.2) target = VerticalSpeed * 0.6f;
            float vUp = Vector3.Dot((Vector3)v.srf_velocity, upv);
            float a = Mathf.Clamp((target - vUp) * Gain, -MaxAccel, MaxAccel);
            rb.AddForce(upv * a, ForceMode.Acceleration);
        }

        void BeginDive(Part p)
        {
            diver = p;
            savedBuoyancy = p.buoyancy;
            p.buoyancy = 0f;
            diverEva = p.FindModuleImplementing<KerbalEVA>();
            if (diverEva != null) { savedSwimSpeed = diverEva.swimSpeed; diverEva.swimSpeed = savedSwimSpeed * SwimBoost; }
        }

        void EndDive()
        {
            if (diver == null) return;
            diver.buoyancy = savedBuoyancy;
            if (diverEva != null) diverEva.swimSpeed = savedSwimSpeed;
            diver = null; diverEva = null;
        }

        static bool NearUnderwaterLair(Vessel v)
        {
            foreach (var d in XenoDatabase.Lairs.Values)
            {
                if (!d.underwater || d.celestialBody != v.mainBody) continue;
                LairRecord rec;
                if (XenoScenario.Instance == null || !XenoScenario.Instance.Lairs.TryGetValue(d.name, out rec)) continue;
                double n, e; Geo.Delta(v.mainBody, rec.lat, rec.lon, v.latitude, v.longitude, out n, out e);
                if (n * n + e * e < 3000.0 * 3000.0) return true;
            }
            return false;
        }

        void OnDestroy() { EndDive(); }
    }
}
