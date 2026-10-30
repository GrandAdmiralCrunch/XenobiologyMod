using UnityEngine;

namespace Xenobiology
{
    /// <summary>A fossil outcrop sitting on the terrain. Static, but re-projected each frame
    /// so it stays glued to the surface through floating-origin shifts.</summary>
    public class FossilSite : MonoBehaviour
    {
        public FossilDef def;
        public CelestialBody body;
        public double lat, lon, alt;
        public string siteId;
        public bool studied;
        public bool announced;
        Vector3 normal;
        bool grounded;
        float glueTimer;

        public Vector3d WorldPos { get { return body.GetWorldSurfacePosition(lat, lon, alt); } }

        public double heading = -1;

        public void Init(FossilDef d, CelestialBody b, double la, double lo, string id, bool isStudied)
        {
            def = d; body = b; lat = la; lon = lo; siteId = id; studied = isStudied;
            alt = Geo.Terrain(b, la, lo);
            Place();
        }

        /// <summary>Distance used for studying. Landmarks are studied at any of their study points (horizontal distance,
        /// shifted so `studyRange` maps onto the normal study range).</summary>
        public double DistanceTo(Vector3d p)
        {
            if (def == null || !def.landmark || def.studyPoints.Count == 0) return (WorldPos - p).magnitude;
            Vector3 up = Geo.Up(body, WorldPos); double best = double.MaxValue;
            foreach (var sp in def.studyPoints)
            {
                Vector3d w = transform.TransformPoint(sp);
                Vector3d d = p - w; d -= (Vector3d)up * Vector3d.Dot(d, up);
                best = System.Math.Min(best, d.magnitude);
            }
            return System.Math.Max(0.0, best - (def.studyRange - XenoSettings.FossilStudyRange));
        }

        public bool lairOwned;

        /// <summary>Fix the site at an exact altitude (a lair's fossil_ marker), e.g. on a cave floor under a rock roof,
        /// where the downward ground ray would hit the roof.</summary>
        public void Pin(double altitude)
        {
            alt = altitude; grounded = true;
            Vector3 u, n_, e_; Geo.Frame(body, lat, lon, out u, out n_, out e_); normal = u;
            Place();
        }

        public void MarkStudied()
        {
            studied = true;
            foreach (Renderer r in GetComponentsInChildren<Renderer>())
                if (r.gameObject.name == "beacon") r.enabled = false;
        }

        void Place()
        {
            if (def.landmark)
            {   // kilometres across: sit level on the terrain height at the centre, never tilt to a local slope
                transform.position = WorldPos;
                Vector3 u0, n0, e0;
                Geo.Frame(body, lat, lon, out u0, out n0, out e0);
                transform.rotation = Quaternion.LookRotation(n0, u0) * Quaternion.Euler(0, (float)(heading >= 0 ? heading : 0), 0);
                return;
            }
            if (!grounded)
            {
                Vector3 n;
                double g = Geo.GroundAltitude(body, lat, lon, alt, out n);
                if (n != Vector3.zero) { alt = g - 0.05 * def.size; normal = n; grounded = true; }
            }
            transform.position = WorldPos;
            Vector3 up, north, east;
            Geo.Frame(body, lat, lon, out up, out north, out east);
            Vector3 u = grounded ? normal : up;
            transform.rotation = Quaternion.LookRotation(Vector3.ProjectOnPlane(north, u), u) * Quaternion.Euler(0, (float)(XenoHash.Hash(siteId) % 360), 0);
        }

        void LateUpdate()
        {
            if (body == null) return;
            Place();
            // once it sits on the ground, glue it to the planet (like a PQSCity) so it no longer needs placing every frame
            glueTimer += Time.deltaTime;
            if (grounded || def.landmark || glueTimer > 8f)       // no terrain collider after 8 s: settle on the PQS height
            {
                Transform parent = body.pqsController != null ? body.pqsController.transform : body.transform;
                transform.SetParent(parent, true);
                enabled = false;
            }
        }

        // ---------------------------------------------------------- procedural outcrops

        public static GameObject Build(FossilDef def, string objName, bool studied)
        {
            if (def.model != null)
            {
                GameObject src = GameDatabase.Instance.GetModelPrefab(def.model.path);
                if (src != null)
                {
                    var r = new GameObject(objName);
                    GameObject m = Object.Instantiate(src);
                    m.SetActive(true);
                    m.transform.SetParent(r.transform, false);
                    m.transform.localPosition = def.model.positionOffset;
                    m.transform.localRotation = Quaternion.Euler(def.model.rotationOffset);
                    m.transform.localScale = Vector3.one * def.model.scale;
                    foreach (Collider c in m.GetComponentsInChildren<Collider>(true)) Object.Destroy(c);
                    r.transform.localScale = Vector3.one * def.size;
                    if (def.landmark && def.studyPoints.Count > 0)
                        foreach (var sp in def.studyPoints) AddBeacon(r.transform, studied, sp + Vector3.up * (def.beaconSize * 4f), def.beaconSize);
                    else AddBeacon(r.transform, studied);
                    return r;
                }
                XenoLog.Warn("Fossil model not found: " + def.model.path);
            }

            var root = new GameObject(objName);
            Color rock = new Color(0.42f, 0.38f, 0.34f);
            Color fossil = def.color;
            Transform slab = Prim(PrimitiveType.Cube, root.transform, new Vector3(0, 0.08f, 0), new Vector3(1.6f, 0.25f, 1.1f), rock, Color.black);
            slab.localRotation = Quaternion.Euler(4f, 0, -3f);

            switch (def.form)
            {
                case FossilForm.Shell:
                    // logarithmic spiral of beads = ammonite-like coil
                    for (int i = 0; i < 26; i++)
                    {
                        float a = i * 0.55f;
                        float r = 0.03f * Mathf.Exp(0.11f * i);
                        float s = 0.03f + r * 0.45f;
                        Prim(PrimitiveType.Sphere, root.transform, new Vector3(Mathf.Cos(a) * r, 0.22f, Mathf.Sin(a) * r), new Vector3(s, s * 0.5f, s), fossil, Color.black);
                    }
                    break;
                case FossilForm.Bones:
                    for (int i = 0; i < 9; i++)
                    {
                        float z = -0.45f + i * 0.11f;
                        Prim(PrimitiveType.Sphere, root.transform, new Vector3(0, 0.22f, z), new Vector3(0.09f, 0.05f, 0.08f), fossil, Color.black);
                        if (i > 1 && i < 7)
                            for (int s = -1; s <= 1; s += 2)
                            {
                                Transform rib = Prim(PrimitiveType.Capsule, root.transform, new Vector3(s * 0.17f, 0.21f, z), new Vector3(0.03f, 0.14f, 0.03f), fossil, Color.black);
                                rib.localRotation = Quaternion.Euler(0, s * 15f, 90f);
                            }
                    }
                    Prim(PrimitiveType.Sphere, root.transform, new Vector3(0, 0.23f, 0.58f), new Vector3(0.22f, 0.09f, 0.26f), fossil, Color.black);
                    break;
                case FossilForm.Trackway:
                    slab.localScale = new Vector3(1.2f, 0.12f, 3.2f);
                    for (int i = 0; i < 7; i++)
                    {
                        float x = (i % 2 == 0 ? -0.22f : 0.22f);
                        float z = -1.3f + i * 0.42f;
                        for (int t = -1; t <= 1; t++)
                            Prim(PrimitiveType.Sphere, root.transform, new Vector3(x + t * 0.07f, 0.13f, z + Mathf.Abs(t) * -0.05f + 0.1f), new Vector3(0.05f, 0.02f, 0.12f), new Color(0.2f, 0.18f, 0.16f), Color.black);
                    }
                    break;
                case FossilForm.Stromatolite:
                    Object.Destroy(slab.gameObject);
                    for (int i = 0; i < 7; i++)
                    {
                        float a = i * 2.4f; float d = i == 0 ? 0 : 0.45f + 0.1f * (i % 3);
                        float h = 0.35f + 0.12f * (i % 4);
                        for (int layer = 0; layer < 4; layer++)
                        {
                            float w = Mathf.Lerp(0.42f, 0.18f, layer / 3f) * (1f - i * 0.04f);
                            Prim(PrimitiveType.Cylinder, root.transform, new Vector3(Mathf.Cos(a) * d, h * layer / 4f + 0.05f, Mathf.Sin(a) * d), new Vector3(w, h / 8f, w),
                                layer % 2 == 0 ? fossil : rock, Color.black);
                        }
                        Prim(PrimitiveType.Sphere, root.transform, new Vector3(Mathf.Cos(a) * d, h + 0.02f, Mathf.Sin(a) * d), new Vector3(0.2f, 0.12f, 0.2f), fossil, Color.black);
                    }
                    break;
                case FossilForm.Amber:
                    Prim(PrimitiveType.Sphere, root.transform, new Vector3(0, 0.3f, 0), new Vector3(0.45f, 0.3f, 0.38f), new Color(0.9f, 0.55f, 0.1f), new Color(0.35f, 0.18f, 0.02f));
                    Prim(PrimitiveType.Sphere, root.transform, new Vector3(0.03f, 0.31f, 0), new Vector3(0.12f, 0.05f, 0.08f), new Color(0.1f, 0.07f, 0.05f), Color.black);
                    break;
            }
            root.transform.localScale = Vector3.one * Mathf.Max(0.1f, def.size);
            AddBeacon(root.transform, studied);
            return root;
        }

        /// <summary>A faint glowing mote above unstudied outcrops so they can be spotted.</summary>
        static void AddBeacon(Transform root, bool studied, Vector3? pos = null, float size = 0.12f)
        {
            Transform b = Prim(PrimitiveType.Sphere, root, pos ?? new Vector3(0, 1.4f, 0), Vector3.one * size, new Color(0.5f, 1f, 0.7f), new Color(0.3f, 0.9f, 0.5f));
            b.gameObject.name = "beacon";
            b.GetComponent<Renderer>().enabled = !studied;
        }

        static Transform Prim(PrimitiveType t, Transform parent, Vector3 pos, Vector3 scale, Color c, Color glow)
        {
            GameObject g = GameObject.CreatePrimitive(t);
            Collider col = g.GetComponent<Collider>();
            if (col != null) Object.Destroy(col);
            g.transform.SetParent(parent, false);
            g.transform.localPosition = pos;
            g.transform.localScale = scale;
            g.GetComponent<Renderer>().sharedMaterial = XenoMaterials.Get(c, glow);
            return g.transform;
        }
    }
}
