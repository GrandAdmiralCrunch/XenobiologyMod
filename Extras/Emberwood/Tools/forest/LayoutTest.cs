using System; using System.IO; using System.Text; using Xenobiology;
class T {
  static void Main(string[] a) {
    var L = new ForestLayout(); L.R = 500; L.seed = a.Length > 0 ? int.Parse(a[0]) : 1; L.entranceBearing = 120;
    string[] names = {"emberleaf","goldenpale","copperoak","torchwood","duskpine","lanternfruit"};
    float[] w = {3,2,1.3f,2,1.1f,0.25f};
    for (int i=0;i<names.Length;i++){ var s=new ForestSpecies{name=names[i],weight=w[i]}; L.species.Add(s);}
    L.species[1].wet=1.2f; L.species[4].high=1; L.species[4].edge=0.8f; L.species[2].footprint=1.5f; L.species[2].maxScale=1.35f; L.species[5].pathside=1.4f; L.species[5].footprint=0.6f;
    L.InitPqs();
    for (int j=0;j<L.pqsN;j++) for (int i=0;i<L.pqsN;i++){ double x=L.PqsX(i), z=L.PqsX(j);
      L.pqs[j*L.pqsN+i]=(float)(150 + x*0.012 - z*0.008 + (ForestLayout.Fbm(x/180,z/180,5,4)-0.5)*14 + (ForestLayout.Noise(x/16,z/16,9)-0.5)*0.6); }
    L.Generate();
    Console.Write(L.log);
    var sb=new StringBuilder("{");
    Func<double[],string> arr = v => "["+string.Join(",", Array.ConvertAll(v, d=>d.ToString("F2")))+"]";
    sb.Append("\"E\":"+L.E+",\"R\":"+L.R+",\"gN\":"+L.gN+",\"mainPath\":"+L.mainPathCount+",");
    sb.Append("\"pool\":"+arr(L.pool)+",\"pond\":"+arr(L.pond)+",\"clearing\":"+arr(L.clearing)+",\"elder\":"+arr(L.elder)+",\"bridge\":"+arr(L.bridge)+",\"cascade\":"+arr(L.cascade)+",\"entrance\":"+arr(L.entrance)+",");
    sb.Append("\"stream\":["+string.Join(",", L.stream.ConvertAll(v=>arr(v)))+"],");
    sb.Append("\"path\":["+string.Join(",", L.path.ConvertAll(v=>arr(v)))+"],");
    sb.Append("\"trees\":["+string.Join(",", L.trees.ConvertAll(t=>string.Format("[{0},{1},{2:F2},{3:F2},{4:F2},{5:F3},{6:F0},{7:F1},{8:F0}]",t.kind,t.variant,t.x,t.y,t.z,t.scale,t.yaw,t.tilt,t.tiltDir)))+"],");
    sb.Append("\"props\":["+string.Join(",", L.props.ConvertAll(t=>string.Format("[{0},{1},{2:F2},{3:F2},{4:F2},{5:F3},{6:F0},{7:F1},{8:F0}]",t.kind,t.variant,t.x,t.y,t.z,t.scale,t.yaw,t.tilt,t.tiltDir)))+"]}");
    File.WriteAllText("layout.json", sb.ToString());
    L.Save("cache.bin"); var L2 = new ForestLayout(); L2.R = L.R; L2.seed = L.seed; L2.InitPqs();
    Console.WriteLine("cache load " + L2.Load("cache.bin") + " trees " + L2.trees.Count + " g " + L2.Ground(10, 20).ToString("F3") + " vs " + L.Ground(10, 20).ToString("F3") + " path " + L2.DistPath(5,5) + "/" + L.DistPath(5,5));
    var bw=new BinaryWriter(File.Create("ground.bin")); foreach(var f in L.ground) bw.Write(f); bw.Close();
    var bp=new BinaryWriter(File.Create("pqs.bin")); for(int j=0;j<L.gN;j+=1) for(int i=0;i<L.gN;i++) bp.Write((float)L.Pqs(-L.E+i,-L.E+j)); bp.Close();
  }
}
