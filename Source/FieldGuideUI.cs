using System;
using System.Collections.Generic;
using System.Linq;
using KSP.UI.Screens;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>
    /// The Xenobiology Field Guide: a catalogue of discovered species, a tree of life per
    /// biosphere that fills in as evidence accumulates, fossils, and panspermia links.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.AllGameScenes, false)]
    public class FieldGuideUI : MonoBehaviour
    {
        enum Tab { Species, Tree, Fossils }
        enum NodeKind { Clade, Species, Microbe, Unknown, PanIn, PanOut }

        class TreeNode
        {
            public NodeKind kind;
            public string label, sub;
            public CladeDef clade; public LifeformDef species; public PanspermiaDef pan; public MicrobeDef microbe;
            public int unknownCount;
            public Color color;
            public bool dashedIn, dottedIn;
            public readonly List<TreeNode> children = new List<TreeNode>();
            public float x, y;
        }

        const int WinId = 0x58454E4F, DbgId = 0x58454E50;
        const float NodeW = 150f, NodeH = 30f, ColW = 190f, RowH = 40f;

        static bool visible;
        bool showDebug;
        Rect win = new Rect(80, 80, 1040, 660);
        Rect dbgWin = new Rect(300, 120, 420, 560);
        Tab tab = Tab.Species;
        string selBio;
        object selected;
        Vector2 scrollList, scrollMain, scrollDetail, scrollDbg;
        ApplicationLauncherButton button;
        Texture2D appIcon, white, unknownSil;
        GUIStyle toggleBtn, small, smallCenter, title, italic, wrap, nodeStyle, header;
        TreeNode treeRoot; float treeW, treeH; bool treeDirty = true;
        const string LockId = "XenobiologyFieldGuide";

        bool SceneOk { get { return HighLogic.LoadedSceneIsFlight || HighLogic.LoadedScene == GameScenes.SPACECENTER || HighLogic.LoadedScene == GameScenes.TRACKSTATION; } }

        void Start()
        {
            if (!SceneOk) { enabled = false; return; }
            white = new Texture2D(1, 1); white.SetPixel(0, 0, Color.white); white.Apply();
            appIcon = GameDatabase.Instance.GetTexture("Xenobiology/Textures/AppIcon", false) ?? white;
            unknownSil = XenoTextures.Get("Xenobiology/Textures/Silhouettes/_unknown");
            if (ApplicationLauncher.Ready) AddButton();
            else GameEvents.onGUIApplicationLauncherReady.Add(AddButton);
            XenoScenario.OnKnowledgeChanged += Dirty;
        }

        void OnDestroy()
        {
            GameEvents.onGUIApplicationLauncherReady.Remove(AddButton);
            XenoScenario.OnKnowledgeChanged -= Dirty;
            if (button != null && ApplicationLauncher.Instance != null) ApplicationLauncher.Instance.RemoveModApplication(button);
            InputLockManager.RemoveControlLock(LockId);
        }

        void Dirty() { treeDirty = true; }

        void AddButton()
        {
            if (button != null || ApplicationLauncher.Instance == null) return;
            button = ApplicationLauncher.Instance.AddModApplication(
                () => { visible = true; treeDirty = true; }, () => { visible = false; },
                null, null, null, null,
                ApplicationLauncher.AppScenes.FLIGHT | ApplicationLauncher.AppScenes.MAPVIEW | ApplicationLauncher.AppScenes.SPACECENTER | ApplicationLauncher.AppScenes.TRACKSTATION,
                appIcon);
            if (visible) button.SetTrue(false);
        }

        bool locked;
        void Update()
        {
            bool alt = Input.GetKey(KeyCode.LeftAlt) || Input.GetKey(KeyCode.RightAlt);
            if (alt && XenoSettings.DebugKey != KeyCode.None && Input.GetKeyDown(XenoSettings.DebugKey)) showDebug = !showDebug;
            if (XenoSettings.FieldGuideKey != KeyCode.None && Input.GetKeyDown(XenoSettings.FieldGuideKey) && GUIUtility.keyboardControl == 0)
            {
                visible = !visible;
                if (button != null) { if (visible) button.SetTrue(false); else button.SetFalse(false); }
            }

            Vector2 m = new Vector2(Input.mousePosition.x, Screen.height - Input.mousePosition.y);
            bool over = (visible && win.Contains(m)) || (showDebug && dbgWin.Contains(m));
            if (over == locked) return;
            locked = over;
            if (over) InputLockManager.SetControlLock(ControlTypes.CAMERACONTROLS | ControlTypes.ALL_SHIP_CONTROLS | ControlTypes.ACTIONS_ALL, LockId);
            else InputLockManager.RemoveControlLock(LockId);
        }

        void InitStyles()
        {
            if (small != null) return;
            small = new GUIStyle(GUI.skin.label) { fontSize = 11, wordWrap = true };
            smallCenter = new GUIStyle(small) { alignment = TextAnchor.UpperCenter };
            title = new GUIStyle(GUI.skin.label) { fontSize = 16, fontStyle = FontStyle.Bold, wordWrap = true };
            header = new GUIStyle(GUI.skin.label) { fontSize = 13, fontStyle = FontStyle.Bold };
            italic = new GUIStyle(GUI.skin.label) { fontSize = 12, fontStyle = FontStyle.Italic, wordWrap = true };
            wrap = new GUIStyle(GUI.skin.label) { fontSize = 12, wordWrap = true };
            nodeStyle = new GUIStyle(GUI.skin.label) { fontSize = 11, alignment = TextAnchor.MiddleCenter, wordWrap = false, clipping = TextClipping.Clip };
            nodeStyle.normal.textColor = Color.white;
            foreach (var st in new[] { small, smallCenter, title, header, italic, wrap, nodeStyle }) st.richText = true;
            toggleBtn = new GUIStyle(GUI.skin.button) { richText = true, alignment = TextAnchor.MiddleLeft, wordWrap = true };
        }

        void OnGUI()
        {
            if (!SceneOk) return;
            GUI.skin = HighLogic.Skin;
            InitStyles();
            if (visible) win = GUILayout.Window(WinId, win, DrawWindow, "Xenobiology Field Guide");
            if (showDebug) dbgWin = GUILayout.Window(DbgId, dbgWin, DrawDebug, "Xenobiology Debug");
        }

        // ================================================================== main window

        List<BiosphereDef> VisibleBiospheres()
        {
            var scen = XenoScenario.Instance;
            return XenoDatabase.Biospheres.Values
                .Where(b => !XenoSettings.SpoilerFree || (scen != null && scen.BiosphereKnown(b)))
                .OrderBy(b => b.displayName).ToList();
        }

        void DrawWindow(int id)
        {
            var scen = XenoScenario.Instance;
            if (scen == null || !XenoDatabase.Loaded)
            {
                GUILayout.Label("Field guide unavailable in this scene.");
                GUI.DragWindow();
                return;
            }
            var bios = VisibleBiospheres();
            if (selBio == null || !bios.Any(b => b.name == selBio)) { selBio = bios.Count > 0 ? bios[0].name : null; treeDirty = true; selected = null; }

            GUILayout.BeginHorizontal();
            // ---- left: biospheres
            GUILayout.BeginVertical(GUILayout.Width(200));
            GUILayout.Label("Biospheres", header);
            scrollList = GUILayout.BeginScrollView(scrollList, GUILayout.Width(200));
            if (bios.Count == 0)
                GUILayout.Label("No extraterrestrial life has been catalogued yet.\n\nSend kerbals out on EVA on promising worlds and use 'Observe Lifeform' when something moves nearby. Scientists can study fossil outcrops.", wrap);
            foreach (var b in bios)
            {
                int total = XenoDatabase.Lifeforms.Values.Count(l => l.parentClade != null && l.parentClade.biosphere == b.name);
                int found = XenoDatabase.Lifeforms.Values.Count(l => l.parentClade != null && l.parentClade.biosphere == b.name && scen.IsDiscovered(l));
                string label = b.displayName + "\n<size=10>" + (b.extinct ? "extinct — " : "") + (total > 0 ? found + "/" + total + " species" : "");
                int mt = MicrobesOf(b).Count();
                if (mt > 0) label += (total > 0 ? " · " : "") + MicrobesOf(b).Count(MicrobeBridge.IsDiscovered) + "/" + mt + " microbes";
                label += "</size>";
                bool on = selBio == b.name;
                if (GUILayout.Toggle(on, label, toggleBtn, GUILayout.MinHeight(38)) && !on) { selBio = b.name; selected = null; treeDirty = true; }
            }
            GUILayout.EndScrollView();
            GUILayout.EndVertical();

            // ---- middle: tabs + content
            GUILayout.BeginVertical(GUILayout.ExpandWidth(true));
            GUILayout.BeginHorizontal();
            foreach (Tab t in Enum.GetValues(typeof(Tab)))
            {
                string n = t == Tab.Tree ? "Tree of Life" : t.ToString();
                if (GUILayout.Toggle(tab == t, n, GUI.skin.button)) tab = t;
            }
            GUILayout.EndHorizontal();
            BiosphereDef bio = selBio != null ? XenoDatabase.Biospheres[selBio] : null;
            if (bio != null)
            {
                switch (tab)
                {
                    case Tab.Species: DrawSpeciesGrid(bio, scen); break;
                    case Tab.Tree: DrawTree(bio, scen); break;
                    case Tab.Fossils: DrawFossils(bio, scen); break;
                }
            }
            GUILayout.EndVertical();

            // ---- right: detail
            GUILayout.BeginVertical(GUILayout.Width(290));
            scrollDetail = GUILayout.BeginScrollView(scrollDetail, GUILayout.Width(290));
            DrawDetail(scen, bio);
            GUILayout.EndScrollView();
            GUILayout.EndVertical();
            GUILayout.EndHorizontal();

            if (GUI.Button(new Rect(win.width - 24, 4, 20, 18), "x")) { visible = false; if (button != null) button.SetFalse(false); }
            GUI.DragWindow(new Rect(0, 0, win.width, 24));
        }

        static IEnumerable<MicrobeDef> MicrobesOf(BiosphereDef b)
        {
            return XenoDatabase.Microbes.Values.Where(m => m.parentClade != null && m.parentClade.biosphere == b.name);
        }

        static Color MicrobeColor(MicrobeDef m)
        {
            switch (m.category)
            {
                case "Bacteria": return new Color(0.25f, 0.45f, 0.55f);
                case "Archaea": return new Color(0.5f, 0.35f, 0.25f);
                case "Fungi": return new Color(0.45f, 0.4f, 0.2f);
                case "Protist": return new Color(0.3f, 0.5f, 0.3f);
                case "Virus": return new Color(0.5f, 0.25f, 0.35f);
                case "Parasite": return new Color(0.45f, 0.2f, 0.2f);
                case "Fossil": return new Color(0.42f, 0.4f, 0.36f);
                default: return new Color(0.35f, 0.35f, 0.42f);
            }
        }

        // ------------------------------------------------------------------ species grid

        void DrawSpeciesGrid(BiosphereDef bio, XenoScenario scen)
        {
            var list = XenoDatabase.Lifeforms.Values.Where(l => l.parentClade != null && l.parentClade.biosphere == bio.name)
                .OrderBy(l => !scen.IsDiscovered(l)).ThenBy(l => l.parentClade.depth).ThenBy(l => l.displayName).ToList();
            int hidden = 0;
            scrollMain = GUILayout.BeginScrollView(scrollMain);
            const float cw = 128, ch = 158;
            float avail = Mathf.Max(cw, win.width - 200 - 290 - 50);
            int perRow = Mathf.Max(1, (int)(avail / (cw + 6)));
            int i = 0;
            GUILayout.BeginHorizontal();
            foreach (var l in list)
            {
                bool known = scen.IsDiscovered(l);
                if (!known && !XenoSettings.ShowUndiscoveredSilhouettes) { hidden++; continue; }
                if (i > 0 && i % perRow == 0) { GUILayout.EndHorizontal(); GUILayout.BeginHorizontal(); }
                i++;
                Rect r = GUILayoutUtility.GetRect(cw, ch, GUILayout.Width(cw), GUILayout.Height(ch));
                bool sel = selected == (object)l;
                GUI.Box(r, "");
                if (sel) DrawFrame(r, new Color(0.5f, 1f, 0.6f), 2);
                Rect img = new Rect(r.x + 8, r.y + 6, cw - 16, cw - 16);
                DrawSilhouette(img, l.silhouetteTex, known ? l.look.color : new Color(0.06f, 0.07f, 0.09f), known);
                GUI.Label(new Rect(r.x + 2, r.y + cw - 8, cw - 4, 36), known ? l.displayName : "???", smallCenter);
                if (GUI.Button(r, "", GUIStyle.none)) selected = l;
            }
            GUILayout.EndHorizontal();
            if (hidden > 0) GUILayout.Label(hidden + " species not yet observed.", italic);
            GUILayout.EndScrollView();
        }

        void DrawSilhouette(Rect r, Texture2D tex, Color tint, bool known)
        {
            Color old = GUI.color;
            Texture2D t = tex ?? unknownSil;
            if (t != null)
            {
                GUI.color = known ? Color.Lerp(tint, Color.white, 0.25f) : tint;
                GUI.DrawTexture(r, t, ScaleMode.ScaleToFit, true);
            }
            else
            {
                GUI.color = new Color(0.15f, 0.15f, 0.18f);
                GUI.DrawTexture(r, white);
                GUI.color = Color.white;
                GUI.Label(r, "?", new GUIStyle(title) { alignment = TextAnchor.MiddleCenter, fontSize = 40 });
            }
            GUI.color = old;
        }

        void DrawFrame(Rect r, Color c, float w)
        {
            Color old = GUI.color; GUI.color = c;
            GUI.DrawTexture(new Rect(r.x, r.y, r.width, w), white);
            GUI.DrawTexture(new Rect(r.x, r.yMax - w, r.width, w), white);
            GUI.DrawTexture(new Rect(r.x, r.y, w, r.height), white);
            GUI.DrawTexture(new Rect(r.xMax - w, r.y, w, r.height), white);
            GUI.color = old;
        }

        // ------------------------------------------------------------------ tree of life

        void BuildTree(BiosphereDef bio, XenoScenario scen)
        {
            treeRoot = null;
            CladeDef root;
            if (string.IsNullOrEmpty(bio.rootClade) || !XenoDatabase.Clades.TryGetValue(bio.rootClade, out root)) return;
            TreeNode r = BuildClade(root, scen);
            if (r == null) return;
            treeRoot = r;
            float row = 0; int maxDepth = 0;
            Layout(treeRoot, 0, ref row, ref maxDepth);
            treeW = (maxDepth + 1) * ColW + 20;
            treeH = row * RowH + 20;
        }

        TreeNode BuildClade(CladeDef c, XenoScenario scen)
        {
            RevealState st = scen.CladeState(c);
            if (st == RevealState.Hidden) return null;
            var n = new TreeNode { kind = NodeKind.Clade, clade = c };
            if (st == RevealState.Revealed) { n.label = c.displayName; n.sub = c.grouping ? "no common ancestor" : c.rank; n.color = c.color * 0.75f; }
            else { n.label = "Unknown lineage"; n.sub = string.Format("evidence {0}/{1}", scen.CladeScore(c), c.revealThreshold); n.color = new Color(0.32f, 0.34f, 0.36f); }

            int unknown = 0;
            foreach (var ch in c.childClades.OrderBy(x => x.displayName))
            {
                TreeNode cn = BuildClade(ch, scen);
                if (cn != null) n.children.Add(cn);
                else unknown += XenoDatabase.AllSpeciesUnder(ch).Count();
            }
            foreach (var s in c.species.OrderBy(x => x.displayName))
            {
                if (scen.IsDiscovered(s))
                    n.children.Add(new TreeNode { kind = NodeKind.Species, species = s, label = s.displayName, sub = s.scientificName, color = s.look.color * 0.6f });
                else unknown++;
            }
            foreach (var m in c.microbes.OrderBy(x => x.name))
            {
                if (MicrobeBridge.IsDiscovered(m))
                    n.children.Add(new TreeNode { kind = NodeKind.Microbe, microbe = m, label = m.name, sub = (m.IsMicrofossil ? "microfossil" : "µ " + m.category.ToLowerInvariant()) + (MicrobeBridge.IsProcessed(m) ? " · lab ✓" : ""), color = MicrobeColor(m) });
                else unknown++;
            }
            if (st == RevealState.Revealed && unknown > 0)
                n.children.Add(new TreeNode { kind = NodeKind.Unknown, unknownCount = unknown, label = "? undescribed", sub = unknown == 1 ? "1 lineage" : unknown + " lineages", color = new Color(0.18f, 0.18f, 0.2f) });

            foreach (var p in XenoDatabase.Panspermia.Values.Where(p => p.source == c && scen.PanspermiaState(p) == RevealState.Revealed))
                n.children.Add(new TreeNode { kind = NodeKind.PanOut, pan = p, label = "Seeded " + p.target.body, sub = p.ageText, color = new Color(0.55f, 0.35f, 0.75f), dashedIn = true });
            if (c.grouping) foreach (var ch in n.children) if (ch.kind == NodeKind.Clade) ch.dottedIn = true;

            // incoming panspermia: an origin node in front of the seeded lineage
            var pin = XenoDatabase.Panspermia.Values.FirstOrDefault(p => p.targetCladeDef == c && scen.PanspermiaState(p) != RevealState.Hidden);
            if (pin != null)
            {
                bool rev = scen.PanspermiaState(pin) == RevealState.Revealed;
                var origin = new TreeNode
                {
                    kind = NodeKind.PanIn, pan = pin,
                    label = rev ? "From " + XenoDatabase.Biospheres[pin.source.biosphere].body : "Anomalous origin?",
                    sub = rev ? pin.source.displayName : "foreign genetic markers",
                    color = new Color(0.55f, 0.35f, 0.75f),
                    dottedIn = n.dottedIn
                };
                n.dashedIn = true; n.dottedIn = false;
                origin.children.Add(n);
                return origin;
            }
            return n;
        }

        void Layout(TreeNode n, int depth, ref float row, ref int maxDepth)
        {
            n.x = 10 + depth * ColW;
            maxDepth = Math.Max(maxDepth, depth);
            if (n.children.Count == 0) { n.y = 10 + row * RowH; row += 1; return; }
            foreach (var c in n.children) Layout(c, depth + 1, ref row, ref maxDepth);
            n.y = (n.children[0].y + n.children[n.children.Count - 1].y) * 0.5f;
        }

        void DrawTree(BiosphereDef bio, XenoScenario scen)
        {
            if (treeDirty) { BuildTree(bio, scen); treeDirty = false; }
            if (treeRoot == null)
            {
                GUILayout.Label("Not enough evidence to sketch this tree of life yet.", italic);
                return;
            }
            GUILayout.Label("Branches resolve as you observe related species and study fossils" + (MicrobeBridge.Installed ? ", and as microbes are sampled and lab-processed (Microbiology Expansion)" : "") + ". Dashed purple links are panspermia events; dotted grey links join lineages with no common ancestor.", small);
            scrollMain = GUILayout.BeginScrollView(scrollMain);
            Rect area = GUILayoutUtility.GetRect(treeW, treeH, GUILayout.Width(treeW), GUILayout.Height(treeH));
            GUI.BeginGroup(area);
            DrawEdges(treeRoot);
            DrawNodes(treeRoot);
            GUI.EndGroup();
            GUILayout.EndScrollView();
        }

        void HLine(float x1, float x2, float y, Color c, bool dashed)
        {
            Color old = GUI.color; GUI.color = c;
            if (x2 < x1) { float t = x1; x1 = x2; x2 = t; }
            if (!dashed) GUI.DrawTexture(new Rect(x1, y - 1, x2 - x1, 2), white);
            else for (float x = x1; x < x2; x += 8) GUI.DrawTexture(new Rect(x, y - 1, Mathf.Min(5, x2 - x), 2), white);
            GUI.color = old;
        }

        void VLine(float x, float y1, float y2, Color c)
        {
            Color old = GUI.color; GUI.color = c;
            if (y2 < y1) { float t = y1; y1 = y2; y2 = t; }
            GUI.DrawTexture(new Rect(x - 1, y1, 2, y2 - y1 + 2), white);
            GUI.color = old;
        }

        void DrawEdges(TreeNode n)
        {
            if (n.children.Count == 0) return;
            float px = n.x + NodeW, py = n.y + NodeH * 0.5f;
            float mid = px + (ColW - NodeW) * 0.5f;
            Color lc = new Color(0.65f, 0.75f, 0.65f, 0.9f);
            HLine(px, mid, py, lc, false);
            float minY = float.MaxValue, maxY = float.MinValue;
            foreach (var c in n.children)
            {
                float cy = c.y + NodeH * 0.5f;
                minY = Mathf.Min(minY, cy); maxY = Mathf.Max(maxY, cy);
                bool pan = c.dashedIn;
                if (c.dottedIn) HLine(mid, c.x, cy, new Color(0.6f, 0.6f, 0.6f, 0.8f), true);
                else HLine(mid, c.x, cy, pan ? new Color(0.75f, 0.5f, 1f) : lc, pan);
                DrawEdges(c);
            }
            VLine(mid, Mathf.Min(minY, py), Mathf.Max(maxY, py), lc);
        }

        void DrawNodes(TreeNode n)
        {
            Rect r = new Rect(n.x, n.y, NodeW, NodeH);
            Color old = GUI.color;
            GUI.color = n.color;
            GUI.DrawTexture(r, white);
            GUI.color = old;
            object key = (object)n.species ?? (object)n.microbe ?? (object)n.clade ?? (object)n.pan;
            bool sel = key != null && selected == key;
            DrawFrame(r, sel ? new Color(0.5f, 1f, 0.6f) : new Color(0, 0, 0, 0.5f), sel ? 2 : 1);
            string txt = "<b>" + n.label + "</b>" + (string.IsNullOrEmpty(n.sub) ? "" : "\n<size=9>" + n.sub + "</size>");
            GUI.Label(r, txt, nodeStyle);
            if (GUI.Button(r, "", GUIStyle.none))
            {
                if (n.kind == NodeKind.PanOut && n.pan != null) { selBio = n.pan.target.name; treeDirty = true; selected = n.pan; }
                else if (n.kind == NodeKind.PanIn && n.pan != null && Event.current.clickCount > 1) { selBio = n.pan.source.biosphere; treeDirty = true; selected = n.pan; }
                else selected = key;
            }
            foreach (var c in n.children) DrawNodes(c);
        }

        // ------------------------------------------------------------------ fossils tab

        void DrawFossils(BiosphereDef bio, XenoScenario scen)
        {
            var list = XenoDatabase.Fossils.Values.Where(f => f.body == bio.body).OrderBy(f => f.displayName).ToList();
            scrollMain = GUILayout.BeginScrollView(scrollMain);
            int unknown = 0;
            foreach (var f in list)
            {
                if (!scen.IsStudied(f)) { unknown++; continue; }
                GUILayout.BeginHorizontal(GUI.skin.box);
                Rect img = GUILayoutUtility.GetRect(64, 64, GUILayout.Width(64), GUILayout.Height(64));
                DrawSilhouette(img, f.silhouetteTex, f.color, true);
                GUILayout.BeginVertical();
                GUILayout.Label("<b>" + f.displayName + "</b>  <size=10>" + f.ageText + "</size>", wrap);
                GUILayout.Label(f.description, small);
                GUILayout.EndVertical();
                GUILayout.EndHorizontal();
                Rect last = GUILayoutUtility.GetLastRect();
                if (GUI.Button(last, "", GUIStyle.none)) selected = f;
            }
            if (list.Count == 0) GUILayout.Label("No fossil record is known on " + bio.body + ".", italic);
            else if (unknown > 0) GUILayout.Label(unknown == list.Count ? "No fossils studied here yet. Look for exposed rock with a faint green glow and bring a scientist." : unknown + " more fossil type(s) remain to be found on " + bio.body + ".", italic);
            GUILayout.EndScrollView();
        }

        // ------------------------------------------------------------------ detail panel

        void DrawDetail(XenoScenario scen, BiosphereDef bio)
        {
            if (selected == null)
            {
                if (bio != null)
                {
                    GUILayout.Label(bio.displayName, title);
                    GUILayout.Label(bio.description, wrap);
                    int clades = XenoDatabase.CladesOf(bio).Count(x => scen.CladeState(x) == RevealState.Revealed);
                    GUILayout.Label(string.Format("Lineages resolved: {0}/{1}", clades, XenoDatabase.CladesOf(bio).Count()), small);
                    int mt = MicrobesOf(bio).Count();
                    if (mt > 0) GUILayout.Label(string.Format("Microbes catalogued: {0}/{1} (lab-processed {2})", MicrobesOf(bio).Count(MicrobeBridge.IsDiscovered), mt, MicrobesOf(bio).Count(MicrobeBridge.IsProcessed)), small);
                    foreach (var p in XenoDatabase.Panspermia.Values.Where(p => (p.target == bio || p.source.biosphere == bio.name) && scen.PanspermiaState(p) == RevealState.Revealed))
                        GUILayout.Label("• " + p.displayName, small);
                }
                return;
            }
            var l = selected as LifeformDef;
            if (l != null) { SpeciesDetail(l, scen); return; }
            var cl = selected as CladeDef;
            if (cl != null) { CladeDetail(cl, scen); return; }
            var f = selected as FossilDef;
            if (f != null) { FossilDetail(f, scen); return; }
            var p2 = selected as PanspermiaDef;
            if (p2 != null) { PanDetail(p2, scen); return; }
            var mc = selected as MicrobeDef;
            if (mc != null) { MicrobeDetail(mc, scen); return; }
        }

        void SpeciesDetail(LifeformDef l, XenoScenario scen)
        {
            bool known = scen.IsDiscovered(l);
            if (known && l.portraitTex != null)
            {
                Rect pr = GUILayoutUtility.GetRect(260, 195, GUILayout.Width(260), GUILayout.Height(195));
                GUI.DrawTexture(pr, l.portraitTex, ScaleMode.ScaleToFit, true);
            }
            else
            {
                Rect img = GUILayoutUtility.GetRect(260, 200, GUILayout.Width(260), GUILayout.Height(200));
                DrawSilhouette(img, l.silhouetteTex, known ? l.look.color : new Color(0.06f, 0.07f, 0.09f), known);
            }
            if (!known)
            {
                GUILayout.Label("Unidentified organism", title);
                GUILayout.Label("Only a silhouette from long-range imagery. Observe it in the field to learn more.", wrap);
                return;
            }
            GUILayout.Label(l.displayName, title);
            if (!string.IsNullOrEmpty(l.scientificName)) GUILayout.Label(l.scientificName, italic);
            GUILayout.Label("<b>Lineage:</b> " + LineageText(l.parentClade, scen), small);
            GUILayout.Label(string.Format("<b>Habitat:</b> {0}   <b>Active:</b> {1}\n<b>Temperament:</b> {2}   <b>Size:</b> {3:0.#} m", l.habitat, l.activeTime == ActivityTime.Any ? "day & night" : l.activeTime.ToString(), l.temperament, l.size), small);
            if (l.biomes.Length > 0) GUILayout.Label("<b>Range:</b> " + string.Join(", ", RangeNames(l)), small);
            if (l.adultDef != null) GUILayout.Label("<b>" + (string.IsNullOrEmpty(l.lifeStage) ? "Juvenile form" : l.lifeStage) + " of:</b> " + (scen.IsDiscovered(l.adultDef) ? l.adultDef.displayName : "an adult form not yet observed"), small);
            foreach (var j in l.juveniles) GUILayout.Label("<b>" + (string.IsNullOrEmpty(j.lifeStage) ? "Juvenile" : j.lifeStage) + ":</b> " + (scen.IsDiscovered(j) ? j.displayName : "not yet observed"), small);
            if (l.diet.Length > 0) GUILayout.Label("<b>Feeds on:</b> " + string.Join(", ", l.diet.Select(d => DietName(d, scen)).Distinct().ToArray()), small);
            GUILayout.Space(4);
            GUILayout.Label(l.description, wrap);
            SpeciesRecord rec;
            if (scen.Species.TryGetValue(l.name, out rec))
            {
                GUILayout.Space(4);
                GUILayout.Label(string.Format("First observed by {0}{1}, {2}. Observations: {3}", rec.discoveredBy,
                    string.IsNullOrEmpty(rec.firstBiome) ? "" : " in " + rec.firstBiome, KSPUtil.PrintDateCompact(rec.firstSeenUT, true), rec.observations), small);
                if (scen.IsAnalysed(l)) GUILayout.Label("<color=#9FE0B0>Lab-analysed: tissue sampled and sequenced.</color>", small);
            }
        }

        static string DietName(string d, XenoScenario scen)
        {
            LifeformDef l; MicrobeDef m;
            if (XenoDatabase.Lifeforms.TryGetValue(d, out l)) return scen.IsDiscovered(l) ? l.displayName : "an unidentified animal";
            if (XenoDatabase.Microbes.TryGetValue(d, out m)) return MicrobeBridge.IsDiscovered(m) ? "<i>" + m.name + "</i>" : "unidentified microbes";
            return d;
        }

        void MicrobeDetail(MicrobeDef m, XenoScenario scen)
        {
            if (m.iconTex != null)
            {
                Rect img = GUILayoutUtility.GetRect(260, 160, GUILayout.Width(260), GUILayout.Height(160));
                GUI.DrawTexture(img, m.iconTex, ScaleMode.ScaleToFit, true);
            }
            GUILayout.Label(m.name, title);
            GUILayout.Label(m.category + " · " + m.hazard + " · from Microbiology Expansion", italic);
            GUILayout.Label("<b>Lineage:</b> " + LineageText(m.parentClade, scen), small);
            if (m.biomes.Length > 0) GUILayout.Label("<b>Found in:</b> " + string.Join(", ", m.biomes) + (string.IsNullOrEmpty(m.situation) || m.situation == "Any" ? "" : " (" + m.situation + ")"), small);
            GUILayout.Label("<b>Lab-processed:</b> " + (MicrobeBridge.IsProcessed(m) ? "yes (+1 lineage evidence)" : "not yet"), small);
            var eats = m.consumes.Where(x => MicrobeBridge.IsDiscovered(x) && MicrobeBridge.IsProcessed(x) && MicrobeBridge.IsProcessed(m)).ToArray();
            if (eats.Length > 0) GUILayout.Label("<b>Consumes:</b> " + string.Join(", ", eats), small);
            var eatenBy = XenoDatabase.Lifeforms.Values.Where(l => l.diet.Contains(m.name) && scen.IsDiscovered(l)).Select(l => l.displayName).ToArray();
            if (eatenBy.Length > 0) GUILayout.Label("<b>Eaten by:</b> " + string.Join(", ", eatenBy), small);
            GUILayout.Space(4);
            GUILayout.Label(m.flavorText, wrap);
        }

        string[] RangeNames(LifeformDef l)
        {
            // stored normalised; show the body's real biome names where they match
            var names = new List<string>();
            if (l.celestialBody != null && l.celestialBody.BiomeMap != null && l.celestialBody.BiomeMap.Attributes != null)
                foreach (var a in l.celestialBody.BiomeMap.Attributes)
                    if (l.biomes.Contains(XenoDatabase.NormBiome(a.name))) names.Add(a.displayname ?? a.name);
            return names.Count > 0 ? names.ToArray() : l.biomes;
        }

        string LineageText(CladeDef c, XenoScenario scen)
        {
            var parts = new List<string>();
            while (c != null)
            {
                parts.Add(scen.CladeState(c) == RevealState.Revealed ? c.displayName : "?");
                c = c.parentClade;
            }
            parts.Reverse();
            return string.Join(" › ", parts.ToArray());
        }

        void CladeDetail(CladeDef c, XenoScenario scen)
        {
            RevealState st = scen.CladeState(c);
            if (st != RevealState.Revealed)
            {
                GUILayout.Label("Unresolved lineage", title);
                GUILayout.Label(string.Format("Evidence: {0} of {1} needed.\nObserve more related species or study fossils to resolve this branch.", scen.CladeScore(c), c.revealThreshold), wrap);
                return;
            }
            GUILayout.Label(c.displayName, title);
            GUILayout.Label(c.rank + (string.IsNullOrEmpty(c.era) ? "" : " · " + c.era), italic);
            GUILayout.Label(c.description, wrap);
            var all = XenoDatabase.AllSpeciesUnder(c).ToList();
            if (all.Count > 0) GUILayout.Label(string.Format("Species catalogued: {0}/{1}", all.Count(scen.IsDiscovered), all.Count), small);
            var mic = XenoDatabase.AllMicrobesUnder(c).ToList();
            if (mic.Count > 0) GUILayout.Label(string.Format("Microbes catalogued: {0}/{1}", mic.Count(MicrobeBridge.IsDiscovered), mic.Count), small);
            if (c.grouping) GUILayout.Label("<i>Not a true clade: the lineages below arose separately and share only a home world.</i>", small);
            if (c.parentClade != null) GUILayout.Label("Within: " + (scen.CladeState(c.parentClade) == RevealState.Revealed ? c.parentClade.displayName : "unresolved lineage"), small);
        }

        void FossilDetail(FossilDef f, XenoScenario scen)
        {
            if (f.portraitTex != null && scen.IsStudied(f))
            {
                Rect pr = GUILayoutUtility.GetRect(260, 195, GUILayout.Width(260), GUILayout.Height(195));
                GUI.DrawTexture(pr, f.portraitTex, ScaleMode.ScaleToFit, true);
            }
            else
            {
                Rect img = GUILayoutUtility.GetRect(260, 160, GUILayout.Width(260), GUILayout.Height(160));
                DrawSilhouette(img, f.silhouetteTex, f.color, true);
            }
            GUILayout.Label(f.displayName, title);
            GUILayout.Label(f.KindLabel + (string.IsNullOrEmpty(f.ageText) ? "" : " · " + f.ageText), italic);
            GUILayout.Label(f.description, wrap);
            var targets = f.evidenceFor.Select(e =>
            {
                CladeDef c; PanspermiaDef p;
                if (XenoDatabase.Clades.TryGetValue(e, out c)) return scen.CladeState(c) == RevealState.Revealed ? c.displayName : "an unresolved lineage";
                if (XenoDatabase.Panspermia.TryGetValue(e, out p)) return scen.PanspermiaState(p) == RevealState.Revealed ? p.displayName : "an anomalous origin";
                return null;
            }).Where(s => s != null).ToArray();
            if (targets.Length > 0) GUILayout.Label("<b>Evidence for:</b> " + string.Join(", ", targets), small);
            FossilRecord rec;
            if (scen.Fossils.TryGetValue(f.name, out rec))
                GUILayout.Label(string.Format("First studied by {0}, {1}. Specimens: {2}", rec.studiedBy, KSPUtil.PrintDateCompact(rec.firstStudiedUT, true), rec.studies), small);
            if (scen.IsAnalysed(f)) GUILayout.Label("<color=#9FE0B0>Lab-analysed: sample sectioned and dated.</color>", small);
        }

        void PanDetail(PanspermiaDef p, XenoScenario scen)
        {
            RevealState st = scen.PanspermiaState(p);
            if (st != RevealState.Revealed)
            {
                GUILayout.Label("Anomalous origin", title);
                GUILayout.Label(string.Format("Something about the deepest roots of {0}'s life doesn't fit. Evidence: {1}/{2}.", p.target.body, scen.PanspermiaScore(p), p.revealThreshold), wrap);
                return;
            }
            GUILayout.Label(p.displayName, title);
            GUILayout.Label(p.mechanism + (string.IsNullOrEmpty(p.ageText) ? "" : " · " + p.ageText), italic);
            GUILayout.Label(string.Format("{0} ({1})  →  {2}{3}", XenoDatabase.Biospheres[p.source.biosphere].body, p.source.displayName, p.target.body,
                p.targetCladeDef != null && p.targetCladeDef.name != p.target.rootClade ? " (" + p.targetCladeDef.displayName + ")" : ""), small);
            GUILayout.Label(p.description, wrap);
        }

        // ================================================================== debug window

        void DrawDebug(int id)
        {
            var scen = XenoScenario.Instance;
            scrollDbg = GUILayout.BeginScrollView(scrollDbg);
            GUILayout.Label(string.Format("Loaded: {0} biospheres, {1} clades, {2} species, {3} fossils, {4} panspermia",
                XenoDatabase.Biospheres.Count, XenoDatabase.Clades.Count, XenoDatabase.Lifeforms.Count, XenoDatabase.Fossils.Count, XenoDatabase.Panspermia.Count), small);
            var sp = XenoSpawner.Instance;
            if (sp != null) GUILayout.Label("Active creatures: " + sp.Creatures.Count + "   fossil sites: " + sp.Sites.Count, small);
            XenoSettings.DebugMode = GUILayout.Toggle(XenoSettings.DebugMode, "Verbose logging");
            XenoSettings.SpoilerFree = GUILayout.Toggle(XenoSettings.SpoilerFree, "Spoiler-free field guide");
            if (scen != null)
            {
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("Discover everything")) scen.DebugDiscoverAll();
                if (GUILayout.Button("Reset discoveries")) scen.DebugReset();
                GUILayout.EndHorizontal();
            }
            Vessel v = FlightGlobals.ActiveVessel;
            if (HighLogic.LoadedSceneIsFlight && sp != null && v != null)
            {
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("Despawn all")) sp.ClearAll();
                if (GUILayout.Button("Put all to sleep")) sp.DebugSleepAll();
                GUILayout.EndHorizontal();
                foreach (var ld in XenoDatabase.Lairs.Values)
                {
                    if (ld.celestialBody != v.mainBody) continue;
                    var lr = LairManager.Site(ld);
                    if (lr == null) continue;
                    double ln, le; Geo.Delta(v.mainBody, v.latitude, v.longitude, lr.lat, lr.lon, out ln, out le);
                    GUILayout.BeginHorizontal();
                    GUILayout.Label(string.Format("Lair {0}: {1:F4}, {2:F4}  ({3:F1} km {4})", ld.displayName, lr.lat, lr.lon, Math.Sqrt(ln * ln + le * le) / 1000.0,
                        Geo.CompassName(Geo.Bearing(v.mainBody, v.latitude, v.longitude, lr.lat, lr.lon))), small);
                    if (!lr.discovered && GUILayout.Button("Reveal", GUILayout.Width(60))) lr.discovered = true;
                    GUILayout.EndHorizontal();
                }
                var here = sp.CandidatesAt(v.mainBody, v.latitude, v.longitude);
                GUILayout.Label("Biome: " + Geo.Biome(v.mainBody, v.latitude, v.longitude) + "  —  can live here: " + (here.Count == 0 ? "none" : string.Join(", ", here.Select(x => x.displayName).ToArray())), small);
                GUILayout.Label("Spawn near active vessel:", header);
                foreach (var l in XenoDatabase.SpeciesOn(v.mainBody))
                    if (!(l.sessile && l.unique && l.model == null))         // fixed lair life (corals) is part of a lair model, not spawnable
                    if (GUILayout.Button(l.displayName + "  [" + l.habitat + ", " + l.look.bodyPlan + "]"))
                    {
                        double la = v.latitude, lo = v.longitude;
                        Geo.Offset(v.mainBody, ref la, ref lo, 25, 0);
                        sp.SpawnGroup(l, v.mainBody, la, lo);
                    }
                foreach (var f in XenoDatabase.FossilsOn(v.mainBody))
                    if (GUILayout.Button("Fossil: " + f.displayName)) sp.DebugSpawnFossil(f, v);
            }
            if (XenoDatabase.Problems.Count > 0)
            {
                GUILayout.Label("Config problems:", header);
                foreach (var p in XenoDatabase.Problems) GUILayout.Label("• " + p, small);
            }
            GUILayout.EndScrollView();
            if (GUILayout.Button("Close")) showDebug = false;
            GUI.DragWindow();
        }
    }
}
