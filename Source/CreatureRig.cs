using System.Collections.Generic;
using UnityEngine;

namespace Xenobiology
{
    public enum CreatureState { Idle, Wander, Alert, Flee, Approach, Follow, Sleep, Takeoff, Glide, Landing, Attack, Burrow, Underground, Emerge, Dive, Screech, Roar, Throw, Leap, Burst, Spent }

    public interface ICreatureRig
    {
        /// <param name="speed">current ground speed in m/s</param>
        /// <param name="actionDuration">length in seconds of the current one-shot state (takeoff, landing, attack)</param>
        void Animate(float dt, float speed, CreatureState state, bool airborne, float actionDuration);
    }

    public static class XenoMaterials
    {
        static Shader diffuse, emissive;
        static readonly Dictionary<string, Material> cache = new Dictionary<string, Material>();

        public static Material Get(Color c, Color glow)
        {
            string key = c.ToString() + glow.ToString();
            Material m;
            if (cache.TryGetValue(key, out m) && m != null) return m;
            bool glows = glow.maxColorComponent > 0.01f;
            if (diffuse == null) diffuse = Shader.Find("KSP/Diffuse") ?? Shader.Find("Diffuse") ?? Shader.Find("Standard");
            if (emissive == null) emissive = Shader.Find("KSP/Emissive/Diffuse") ?? diffuse;
            m = new Material(glows ? emissive : diffuse);
            m.color = c;
            if (glows)
            {
                if (m.HasProperty("_EmissiveColor")) m.SetColor("_EmissiveColor", glow);
                if (m.HasProperty("_EmissionColor")) { m.SetColor("_EmissionColor", glow); m.EnableKeyword("_EMISSION"); }
            }
            cache[key] = m;
            return m;
        }
    }

    /// <summary>
    /// Builds a creature out of Unity primitives from a handful of proportions, and animates it
    /// procedurally (gait, wing beats, undulation, pulsing). Lets config-only modders get moving,
    /// animated wildlife without touching Blender. Local frame: +Z forward, +Y up, origin at the feet.
    /// </summary>
    public class ProceduralRig : MonoBehaviour, ICreatureRig
    {
        class Limb { public Transform t; public float phase; public Vector3 axis; public float amp; public Quaternion rest; }

        ProceduralLook look;
        readonly List<Limb> legs = new List<Limb>();
        readonly List<Limb> wings = new List<Limb>();
        readonly List<Transform> spine = new List<Transform>();       // serpent / tail segments
        readonly List<Vector3> spineRest = new List<Vector3>();
        readonly List<Transform> tentacles = new List<Transform>();
        Transform body, head, tailFin, bell;
        Vector3 bodyRest, bellScale;
        float phase;

        public static GameObject Build(LifeformDef def, string objName)
        {
            var root = new GameObject(objName);
            var rig = root.AddComponent<ProceduralRig>();
            rig.look = def.look;
            rig.Construct();
            root.transform.localScale = Vector3.one * Mathf.Max(0.05f, def.size);
            return root;
        }

        Transform Prim(PrimitiveType type, Transform parent, Vector3 pos, Vector3 scale, Color c, Color glow, string n)
        {
            GameObject g = GameObject.CreatePrimitive(type);
            g.name = n;
            Collider col = g.GetComponent<Collider>();
            if (col != null) Destroy(col);
            g.transform.SetParent(parent, false);
            g.transform.localPosition = pos;
            g.transform.localScale = scale;
            Renderer r = g.GetComponent<Renderer>();
            r.sharedMaterial = XenoMaterials.Get(c, glow);
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            g.layer = 0;
            return g.transform;
        }

        Transform Pivot(Transform parent, Vector3 pos, string n)
        {
            var g = new GameObject(n);
            g.transform.SetParent(parent, false);
            g.transform.localPosition = pos;
            return g.transform;
        }

        void Eyes(Transform h, float r, float forward)
        {
            int n = look.eyes;
            Color eyeGlow = look.glowColor.maxColorComponent > 0.01f ? look.glowColor : Color.black;
            for (int i = 0; i < n; i++)
            {
                float t = n == 1 ? 0f : (i / (float)(n - 1) - 0.5f);
                float x = t * r * 1.1f;
                float y = r * 0.25f + (i % 2 == 1 && n > 2 ? r * 0.2f : 0f);
                Prim(PrimitiveType.Sphere, h, new Vector3(x, y, forward), Vector3.one * r * 0.28f, new Color(0.05f, 0.05f, 0.05f), eyeGlow, "eye" + i);
            }
        }

        void Construct()
        {
            switch (look.bodyPlan)
            {
                case BodyPlan.Quadruped: BuildLegged(4); break;
                case BodyPlan.Hexapod: BuildLegged(6); break;
                case BodyPlan.Serpent: BuildSerpent(); break;
                case BodyPlan.Avian: BuildAvian(); break;
                case BodyPlan.Fish: BuildFish(); break;
                case BodyPlan.Floater: BuildFloater(); break;
                default: BuildBlob(); break;
            }
        }

        void BuildLegged(int count)
        {
            float L = look.bodyLength, W = look.bodyWidth, Lg = look.legLength, H = look.headSize;
            float bodyY = Lg + W * 0.35f;
            body = Pivot(transform, new Vector3(0, bodyY, 0), "body");
            bodyRest = body.localPosition;
            if (count == 6)
            {
                // three-part arthropod-ish body
                Prim(PrimitiveType.Sphere, body, new Vector3(0, 0, L * 0.05f), new Vector3(W, W * 0.7f, L * 0.4f), look.color, Color.black, "thorax");
                Prim(PrimitiveType.Sphere, body, new Vector3(0, W * 0.05f, -L * 0.35f), new Vector3(W * 1.15f, W * 0.8f, L * 0.55f), look.accentColor, look.glowColor * 0.5f, "abdomen");
            }
            else
            {
                Prim(PrimitiveType.Sphere, body, Vector3.zero, new Vector3(W, W * 0.85f, L), look.color, Color.black, "torso");
                Prim(PrimitiveType.Sphere, body, new Vector3(0, W * 0.3f, -L * 0.05f), new Vector3(W * 0.6f, W * 0.4f, L * 0.8f), look.accentColor, look.glowColor * 0.5f, "back");
            }
            head = Pivot(body, new Vector3(0, W * 0.25f, L * 0.5f + H * 0.3f), "headPivot");
            Prim(PrimitiveType.Sphere, head, Vector3.zero, new Vector3(H, H * 0.85f, H * 1.2f), look.color, Color.black, "head");
            Eyes(head, H, H * 0.5f);
            if (count == 6)
            {
                for (int s = -1; s <= 1; s += 2)
                {
                    Transform a = Pivot(head, new Vector3(s * H * 0.25f, H * 0.35f, H * 0.3f), "antenna");
                    a.localRotation = Quaternion.Euler(-35f, s * 20f, 0);
                    Prim(PrimitiveType.Cylinder, a, new Vector3(0, H * 0.5f, 0), new Vector3(0.04f, H * 0.5f, 0.04f), look.accentColor, look.glowColor, "stalk");
                    legs.Add(new Limb { t = a, phase = s * 0.8f, axis = Vector3.right, amp = 8f, rest = a.localRotation });
                }
            }
            int pairs = count / 2;
            for (int i = 0; i < pairs; i++)
            {
                float z = pairs == 1 ? 0 : Mathf.Lerp(L * 0.32f, -L * 0.32f, i / (float)(pairs - 1));
                for (int s = -1; s <= 1; s += 2)
                {
                    Transform hip = Pivot(body, new Vector3(s * W * 0.42f, -W * 0.15f, z), "hip");
                    if (count == 6) hip.localRotation = Quaternion.Euler(0, 0, s * 25f);
                    float thick = Mathf.Max(0.05f, W * (count == 6 ? 0.12f : 0.22f));
                    float legLen = Lg + W * 0.2f;
                    Prim(PrimitiveType.Cylinder, hip, new Vector3(0, -legLen * 0.5f, 0), new Vector3(thick, legLen * 0.5f, thick), look.accentColor, Color.black, "leg");
                    // diagonal gait: opposite corners in phase
                    float ph = ((i % 2 == 0) ^ (s > 0)) ? 0f : Mathf.PI;
                    legs.Add(new Limb { t = hip, phase = ph, axis = Vector3.right, amp = 28f, rest = hip.localRotation });
                }
            }
            // tail
            if (look.tailLength > 0.01f)
            {
                Transform prev = Pivot(body, new Vector3(0, W * 0.1f, -L * 0.5f), "tail");
                int segs = 4;
                for (int i = 0; i < segs; i++)
                {
                    float sz = Mathf.Lerp(W * 0.35f, W * 0.1f, i / (float)segs);
                    Prim(PrimitiveType.Sphere, prev, new Vector3(0, 0, -look.tailLength / segs * 0.5f), new Vector3(sz, sz, look.tailLength / segs * 1.3f), look.color, Color.black, "tailSeg");
                    spine.Add(prev); spineRest.Add(prev.localEulerAngles);
                    if (i < segs - 1) prev = Pivot(prev, new Vector3(0, 0, -look.tailLength / segs), "tailJoint");
                }
            }
        }

        void BuildSerpent()
        {
            float L = look.bodyLength, W = look.bodyWidth, H = look.headSize;
            int n = look.segments;
            float segLen = L / n;
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)(n - 1);
                float w = W * Mathf.Lerp(1f, 0.35f, t * t);
                Transform s = Pivot(transform, new Vector3(0, W * 0.5f, L * 0.5f - i * segLen), "seg" + i);
                Prim(PrimitiveType.Sphere, s, Vector3.zero, new Vector3(w, w * 0.8f, segLen * 1.6f), (i % 2 == 0) ? look.color : look.accentColor, i % 3 == 0 ? look.glowColor : Color.black, "segMesh");
                spine.Add(s); spineRest.Add(s.localPosition);
            }
            head = Pivot(spine[0], new Vector3(0, W * 0.1f, segLen * 0.6f + H * 0.4f), "head");
            Prim(PrimitiveType.Sphere, head, Vector3.zero, new Vector3(H * 1.1f, H * 0.7f, H * 1.4f), look.color, Color.black, "headMesh");
            Eyes(head, H, H * 0.55f);
        }

        void BuildAvian()
        {
            float L = look.bodyLength, W = look.bodyWidth, H = look.headSize, Lg = look.legLength;
            body = Pivot(transform, new Vector3(0, Lg + W * 0.5f, 0), "body");
            bodyRest = body.localPosition;
            Prim(PrimitiveType.Sphere, body, Vector3.zero, new Vector3(W, W * 0.9f, L), look.color, Color.black, "torso");
            head = Pivot(body, new Vector3(0, W * 0.35f, L * 0.5f + H * 0.2f), "head");
            Prim(PrimitiveType.Sphere, head, Vector3.zero, Vector3.one * H, look.color, Color.black, "headMesh");
            Prim(PrimitiveType.Sphere, head, new Vector3(0, -H * 0.1f, H * 0.6f), new Vector3(H * 0.25f, H * 0.2f, H * 0.8f), look.accentColor, Color.black, "beak");
            Eyes(head, H, H * 0.4f);
            float half = look.wingSpan * 0.5f;
            for (int s = -1; s <= 1; s += 2)
            {
                Transform sh = Pivot(body, new Vector3(s * W * 0.4f, W * 0.2f, L * 0.1f), "shoulder");
                Prim(PrimitiveType.Cube, sh, new Vector3(s * half * 0.5f, 0, -L * 0.1f), new Vector3(half, 0.03f, L * 0.55f), look.accentColor, look.glowColor * 0.6f, "wing");
                Prim(PrimitiveType.Cube, sh, new Vector3(s * half * 0.85f, 0, -L * 0.25f), new Vector3(half * 0.35f, 0.025f, L * 0.4f), look.color, Color.black, "wingtip");
                wings.Add(new Limb { t = sh, phase = 0, axis = Vector3.forward * s, amp = 38f, rest = sh.localRotation });
            }
            tailFin = Pivot(body, new Vector3(0, 0, -L * 0.5f), "tail");
            Prim(PrimitiveType.Cube, tailFin, new Vector3(0, 0, -look.tailLength * 0.4f), new Vector3(W * 0.9f, 0.03f, look.tailLength * 0.8f), look.accentColor, Color.black, "tailFan");
            for (int s = -1; s <= 1; s += 2)
            {
                Transform hip = Pivot(body, new Vector3(s * W * 0.2f, -W * 0.3f, 0), "hip");
                Prim(PrimitiveType.Cylinder, hip, new Vector3(0, -Lg * 0.5f, 0), new Vector3(0.05f, Lg * 0.5f, 0.05f), look.accentColor, Color.black, "leg");
                legs.Add(new Limb { t = hip, phase = s > 0 ? 0 : Mathf.PI, axis = Vector3.right, amp = 25f, rest = hip.localRotation });
            }
        }

        void BuildFish()
        {
            float L = look.bodyLength, W = look.bodyWidth, H = look.headSize;
            body = Pivot(transform, new Vector3(0, W * 0.5f, 0), "body");
            bodyRest = body.localPosition;
            Prim(PrimitiveType.Sphere, body, Vector3.zero, new Vector3(W * 0.6f, W, L), look.color, Color.black, "torso");
            Prim(PrimitiveType.Sphere, body, new Vector3(0, -W * 0.2f, 0.05f), new Vector3(W * 0.5f, W * 0.6f, L * 0.85f), look.accentColor, look.glowColor, "belly");
            Prim(PrimitiveType.Cube, body, new Vector3(0, W * 0.55f, -L * 0.05f), new Vector3(0.03f, W * 0.5f, L * 0.35f), look.accentColor, Color.black, "dorsal");
            head = Pivot(body, new Vector3(0, 0, L * 0.4f), "head");
            Eyes(head, H, H * 0.1f);
            tailFin = Pivot(body, new Vector3(0, 0, -L * 0.45f), "tailPivot");
            Prim(PrimitiveType.Cube, tailFin, new Vector3(0, 0, -look.tailLength * 0.35f), new Vector3(0.03f, W * 1.1f, look.tailLength * 0.7f), look.accentColor, look.glowColor * 0.5f, "tailFin");
            for (int s = -1; s <= 1; s += 2)
            {
                Transform p = Pivot(body, new Vector3(s * W * 0.3f, -W * 0.15f, L * 0.15f), "pectoral");
                Prim(PrimitiveType.Cube, p, new Vector3(s * W * 0.2f, 0, -0.05f), new Vector3(W * 0.4f, 0.02f, L * 0.15f), look.accentColor, Color.black, "fin");
                wings.Add(new Limb { t = p, phase = s > 0 ? 0 : Mathf.PI, axis = Vector3.forward * s, amp = 20f, rest = p.localRotation });
            }
        }

        void BuildFloater()
        {
            float W = look.bodyWidth * 2f, L = look.bodyLength, H = look.headSize;
            bell = Pivot(transform, new Vector3(0, L, 0), "bell");
            Prim(PrimitiveType.Sphere, bell, Vector3.zero, new Vector3(W, W * 0.6f, W), look.color, look.glowColor * 0.6f, "dome");
            Prim(PrimitiveType.Sphere, bell, new Vector3(0, -W * 0.12f, 0), new Vector3(W * 0.7f, W * 0.35f, W * 0.7f), look.accentColor, look.glowColor, "core");
            bellScale = bell.localScale;
            int n = Mathf.Clamp(look.segments, 3, 12);
            for (int i = 0; i < n; i++)
            {
                float a = i * Mathf.PI * 2f / n;
                Transform t = Pivot(bell, new Vector3(Mathf.Cos(a) * W * 0.35f, -W * 0.2f, Mathf.Sin(a) * W * 0.35f), "tentacle" + i);
                float len = L * 0.9f;
                Prim(PrimitiveType.Cylinder, t, new Vector3(0, -len * 0.5f, 0), new Vector3(0.04f, len * 0.5f, 0.04f), look.accentColor, look.glowColor, "strand");
                tentacles.Add(t);
            }
            if (look.eyes > 0) { head = bell; Eyes(bell, H, W * 0.45f); }
        }

        void BuildBlob()
        {
            float W = look.bodyWidth * 2f;
            body = Pivot(transform, new Vector3(0, W * 0.4f, 0), "body");
            bodyRest = body.localPosition;
            Prim(PrimitiveType.Sphere, body, Vector3.zero, new Vector3(W, W * 0.8f, W * look.bodyLength), look.color, look.glowColor * 0.4f, "blob");
            head = body;
            Eyes(body, look.headSize, W * 0.45f * look.bodyLength);
        }

        // --------------------------------------------------------------- animation

        public void Animate(float dt, float speed, CreatureState state, bool airborne, float actionDuration)
        {
            if (state == CreatureState.Sleep) speed = 0f;
            if (airborne && state == CreatureState.Glide) state = CreatureState.Wander;
            float moving = Mathf.Clamp01(Mathf.Abs(speed) / 0.5f);
            float freq = 1.2f + speed * 1.4f;
            if (look.bodyPlan == BodyPlan.Avian) freq = 3f + speed * 0.3f;
            float pace = state == CreatureState.Sleep ? 0.08f : (moving > 0.05f || look.bodyPlan == BodyPlan.Floater || look.bodyPlan == BodyPlan.Avian ? 1f : 0.25f);
            phase += dt * freq * Mathf.PI * 2f * pace;

            foreach (var l in legs)
            {
                float a = Mathf.Sin(phase + l.phase) * l.amp * moving;
                l.t.localRotation = l.rest * Quaternion.AngleAxis(a, l.axis);
            }

            bool flying = look.bodyPlan == BodyPlan.Avian && (airborne || state == CreatureState.Takeoff || (state != CreatureState.Idle && state != CreatureState.Sleep && speed > 0.5f));
            foreach (var w in wings)
            {
                float amp = look.bodyPlan == BodyPlan.Avian ? (flying ? w.amp : 4f) : w.amp;
                float glide = look.bodyPlan == BodyPlan.Avian && state == CreatureState.Wander ? Mathf.Clamp01(Mathf.Sin(phase * 0.13f) + 0.3f) : 1f;
                float a = (Mathf.Sin(phase + w.phase) * amp * glide) + (look.bodyPlan == BodyPlan.Avian && !flying ? -70f : 0f);
                w.t.localRotation = w.rest * Quaternion.AngleAxis(a, w.axis);
            }

            if (body != null && look.bodyPlan != BodyPlan.Floater)
            {
                float bob = Mathf.Abs(Mathf.Sin(phase)) * 0.03f * moving;
                float breathe = Mathf.Sin(Time.time * 1.7f) * 0.008f;
                body.localPosition = bodyRest + new Vector3(0, bob + breathe, 0);
                if (look.bodyPlan == BodyPlan.Fish) body.localRotation = Quaternion.Euler(0, Mathf.Sin(phase) * 6f, 0);
                if (look.bodyPlan == BodyPlan.Blob)
                {
                    float sq = 1f + Mathf.Sin(phase * 0.8f) * 0.08f * (0.4f + moving);
                    body.localScale = new Vector3(1f / Mathf.Sqrt(sq), sq, 1f / Mathf.Sqrt(sq));
                }
            }

            if (head != null && head != body && head != bell)
            {
                float look1 = state == CreatureState.Idle ? Mathf.Sin(Time.time * 0.6f + phase * 0.05f) * 25f : 0f;
                float up = state == CreatureState.Alert ? -15f : 0f;
                head.localRotation = Quaternion.Euler(up, look1, 0);
            }

            if (tailFin != null)
            {
                float a = Mathf.Sin(phase) * (look.bodyPlan == BodyPlan.Fish ? 30f : 8f);
                tailFin.localRotation = Quaternion.Euler(look.bodyPlan == BodyPlan.Avian ? a * 0.3f : 0f, look.bodyPlan == BodyPlan.Fish ? a : 0f, 0);
            }

            if (look.bodyPlan == BodyPlan.Serpent)
            {
                float amp = look.bodyWidth * (0.6f + moving * 0.8f);
                for (int i = 0; i < spine.Count; i++)
                {
                    float k = i / (float)spine.Count;
                    Vector3 p = spineRest[i];
                    p.x = Mathf.Sin(phase - i * 0.7f) * amp * Mathf.Lerp(0.3f, 1f, k);
                    spine[i].localPosition = p;
                }
            }
            else
            {
                for (int i = 0; i < spine.Count; i++)
                    spine[i].localRotation = Quaternion.Euler(spineRest[i].x, Mathf.Sin(Time.time * 2f + phase * 0.3f - i * 0.6f) * (10f + 10f * moving), 0);
            }

            if (bell != null)
            {
                float pulse = Mathf.Sin(phase * 0.5f);
                bell.localScale = new Vector3(bellScale.x * (1f + pulse * 0.1f), bellScale.y * (1f - pulse * 0.12f), bellScale.z * (1f + pulse * 0.1f));
                for (int i = 0; i < tentacles.Count; i++)
                    tentacles[i].localRotation = Quaternion.Euler(Mathf.Sin(phase * 0.5f + i) * 12f + speed * 6f, 0, Mathf.Cos(phase * 0.4f + i * 1.7f) * 10f);
            }
        }
    }

    /// <summary>Wraps a hand-made model and drives its legacy Animation clips by state.</summary>
    public class ModelRig : MonoBehaviour, ICreatureRig
    {
        ModelInfo info;
        Animation[] anims;
        string current;
        CreatureController ctrl;

        public static GameObject Build(LifeformDef def, ModelInfo info, string objName)
        {
            GameObject src = GameDatabase.Instance.GetModelPrefab(info.path);
            if (src == null) { XenoLog.Warn("Model not found: " + info.path + " (" + objName + "); falling back to procedural body"); return null; }
            var root = new GameObject(objName);
            GameObject m = Instantiate(src);
            m.SetActive(true);
            m.transform.SetParent(root.transform, false);
            m.transform.localPosition = info.positionOffset;
            m.transform.localRotation = Quaternion.Euler(info.rotationOffset);
            m.transform.localScale = Vector3.one * info.scale;
            foreach (Collider c in m.GetComponentsInChildren<Collider>(true)) Destroy(c);
            foreach (Rigidbody rb in m.GetComponentsInChildren<Rigidbody>(true)) Destroy(rb);
            // hand-made models are used at their authored size (x MODEL scale); `size` is the creature's
            // real length for gameplay logic and the field guide.
            // Skinning and animation only run while a creature is on screen. Instead of recomputing the bounds every frame
            // (updateWhenOffscreen, which forces full skinning even off-screen), the rest-pose bounds are padded so that
            // spread wings, lunges and swinging tentacles never get culled by mistake.
            foreach (SkinnedMeshRenderer smr in m.GetComponentsInChildren<SkinnedMeshRenderer>(true))
            {
                smr.updateWhenOffscreen = false;
                Bounds b = smr.localBounds;
                b.Expand(b.size.magnitude * 0.6f);
                smr.localBounds = b;
            }
            var rig = root.AddComponent<ModelRig>();
            rig.info = info;
            rig.anims = m.GetComponentsInChildren<Animation>(true);
            foreach (Animation a in rig.anims) { a.cullingType = AnimationCullingType.BasedOnRenderers; a.playAutomatically = false; }
            return root;
        }

        CreatureState lastState;

        static bool OneShot(CreatureState s) { return s == CreatureState.Takeoff || s == CreatureState.Landing || s == CreatureState.Attack || s == CreatureState.Burrow || s == CreatureState.Emerge || s == CreatureState.Roar || s == CreatureState.Throw || s == CreatureState.Burst; }

        public void Animate(float dt, float speed, CreatureState state, bool airborne, float actionDuration)
        {
            string want;
            float aspeed = Mathf.Abs(speed);
            switch (state)
            {
                case CreatureState.Sleep: want = info.sleepAnim; break;
                case CreatureState.Takeoff: want = info.takeoffAnim ?? info.glideAnim; break;
                case CreatureState.Landing: want = info.landAnim ?? info.idleAnim; break;
                case CreatureState.Attack: want = info.attackAnim ?? info.alertAnim; break;
                case CreatureState.Glide: want = info.glideAnim; break;
                case CreatureState.Burrow: want = info.digAnim ?? info.idleAnim; break;
                case CreatureState.Underground: want = info.idleAnim; break;
                case CreatureState.Emerge: want = info.emergeAnim ?? info.idleAnim; break;
                case CreatureState.Dive: want = info.diveAnim; break;
                case CreatureState.Screech: want = info.screechAnim; break;
                case CreatureState.Roar: want = info.roarAnim ?? info.alertAnim; break;
                case CreatureState.Throw: want = info.throwAnim ?? info.attackAnim ?? info.alertAnim; break;
                case CreatureState.Leap: want = info.leapAnim ?? info.fleeAnim ?? info.moveAnim; break;
                case CreatureState.Burst: want = info.burstAnim ?? info.alertAnim; break;
                case CreatureState.Spent: want = info.idleAnim; break;
                case CreatureState.Flee: want = airborne ? info.glideAnim : (aspeed > 0.3f ? info.fleeAnim : info.alertAnim); break;
                case CreatureState.Alert: want = airborne ? info.glideAnim : info.alertAnim; break;
                default: want = airborne ? info.glideAnim : (aspeed > 0.3f ? info.moveAnim : info.idleAnim); break;
            }
            if (ctrl == null) ctrl = GetComponent<CreatureController>();
            bool swimming = false;
            if (ctrl != null)
            {
                // flyers flap while climbing or fleeing, and glide otherwise
                if (airborne && want == info.glideAnim && !string.IsNullOrEmpty(info.flapAnim) && (ctrl.vSpeed > 0.4f || state == CreatureState.Flee || state == CreatureState.Alert))
                    want = info.flapAnim;
                // swimmers paddle at the surface instead of walking or running
                if (ctrl.Swimming && !string.IsNullOrEmpty(info.swimAnim) && (want == info.moveAnim || want == info.fleeAnim || want == info.idleAnim || want == info.alertAnim))
                {
                    swimming = true;
                    want = aspeed > 0.3f ? info.swimAnim : info.floatAnim;
                }
            }
            bool restart = OneShot(state) && state != lastState;
            lastState = state;
            if (string.IsNullOrEmpty(want) || anims == null) { current = want; return; }
            foreach (Animation a in anims)
            {
                AnimationState st = a[want];
                if (st == null) continue;
                if (OneShot(state))
                {
                    st.wrapMode = WrapMode.ClampForever;
                    st.speed = actionDuration > 0.01f ? st.length / actionDuration : 1f;
                    if (restart) { a.Stop(want); st.time = 0f; a.CrossFade(want, 0.12f); }
                    continue;
                }
                st.wrapMode = WrapMode.Loop;
                float native = swimming && want == info.swimAnim ? info.swimAnimSpeed
                             : want == info.fleeAnim && info.fleeAnimSpeed > 0f ? info.fleeAnimSpeed
                             : want == info.moveAnim && info.moveAnimSpeed > 0f ? info.moveAnimSpeed : 0f;
                st.speed = native > 0f ? Mathf.Clamp(aspeed / native, 0.3f, 2.5f) * Mathf.Sign(speed == 0 ? 1 : speed) : 1f;
                if (current != want || !a.isPlaying) a.CrossFade(want, want == info.sleepAnim ? 0.8f : 0.3f);
            }
            current = want;
        }
    }
}
