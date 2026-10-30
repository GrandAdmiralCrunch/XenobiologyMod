using System;
using UnityEngine;

namespace Xenobiology
{
    /// <summary>Surface-coordinate helpers. Everything is stored as lat/lon/alt so it survives
    /// KSP's floating origin shifts and planet rotation.</summary>
    public static class Geo
    {
        public const double Deg2Rad = Math.PI / 180.0;
        public const double Rad2Deg = 180.0 / Math.PI;
        public const int SceneryMask = 1 << 15; // "Local Scenery" (PQS terrain colliders)

        public static double WrapLon(double lon)
        {
            while (lon > 180) lon -= 360;
            while (lon < -180) lon += 360;
            return lon;
        }

        /// <summary>Move (lat,lon) by metres north/east.</summary>
        public static void Offset(CelestialBody b, ref double lat, ref double lon, double north, double east)
        {
            double r = b.Radius;
            lat += north / r * Rad2Deg;
            double c = Math.Cos(lat * Deg2Rad);
            if (Math.Abs(c) < 1e-4) c = 1e-4;
            lon = WrapLon(lon + east / (r * c) * Rad2Deg);
            if (lat > 89.9) lat = 89.9;
            if (lat < -89.9) lat = -89.9;
        }

        /// <summary>Metres north/east from point A to point B (small-distance approximation).</summary>
        public static void Delta(CelestialBody b, double lat1, double lon1, double lat2, double lon2, out double north, out double east)
        {
            double r = b.Radius;
            north = (lat2 - lat1) * Deg2Rad * r;
            east = WrapLon(lon2 - lon1) * Deg2Rad * r * Math.Cos((lat1 + lat2) * 0.5 * Deg2Rad);
        }

        /// <summary>Compass heading (deg, 0 = north, 90 = east) from A to B.</summary>
        public static double Bearing(CelestialBody b, double lat1, double lon1, double lat2, double lon2)
        {
            double n, e; Delta(b, lat1, lon1, lat2, lon2, out n, out e);
            return (Math.Atan2(e, n) * Rad2Deg + 360.0) % 360.0;
        }

        /// <summary>False for gas giants: no terrain and no ocean, only sky.</summary>
        public static bool HasSurface(CelestialBody b) { return b.pqsController != null || b.ocean; }

        /// <summary>Terrain height above sea level (negative = sea floor).</summary>
        public static double Terrain(CelestialBody b, double lat, double lon)
        {
            if (b.pqsController == null) return 0;
            return b.TerrainAltitude(lat, lon, true);
        }

        /// <summary>Precise ground altitude using loaded terrain colliders when available.</summary>
        public static double GroundAltitude(CelestialBody b, double lat, double lon, double guess, out Vector3 normal, double headroom = 60.0)
        {
            normal = Vector3.zero;
            Vector3d top = b.GetWorldSurfacePosition(lat, lon, guess + headroom);
            Vector3d up = (top - b.position).normalized;
            RaycastHit hit;
            if (Physics.Raycast(top, -up, out hit, (float)headroom + 140f, SceneryMask, QueryTriggerInteraction.Ignore))
            {
                normal = hit.normal;
                return b.GetAltitude(hit.point);
            }
            return guess;
        }

        public static Vector3 Up(CelestialBody b, Vector3d worldPos) { return (worldPos - b.position).normalized; }

        /// <summary>World-space unit vectors for north and east at a surface point.</summary>
        public static void Frame(CelestialBody b, double lat, double lon, out Vector3 up, out Vector3 north, out Vector3 east)
        {
            up = b.GetSurfaceNVector(lat, lon);
            Vector3 axis = b.transform.up;
            north = Vector3.ProjectOnPlane(axis, up).normalized;
            if (north.sqrMagnitude < 0.5f) north = Vector3.ProjectOnPlane(b.transform.forward, up).normalized;
            // east: direction of increasing longitude, measured numerically to avoid handedness doubts
            Vector3d p0 = b.GetWorldSurfacePosition(lat, lon, 0);
            Vector3d p1 = b.GetWorldSurfacePosition(lat, lon + 0.001, 0);
            east = Vector3.ProjectOnPlane((Vector3)(p1 - p0), up).normalized;
        }

        public static bool IsDaylight(CelestialBody b, double lat, double lon)
        {
            if (Planetarium.fetch == null || Planetarium.fetch.Sun == null || b == Planetarium.fetch.Sun) return true;
            Vector3d p = b.GetWorldSurfacePosition(lat, lon, 0);
            Vector3d toSun = (Planetarium.fetch.Sun.position - p).normalized;
            return Vector3d.Dot(b.GetSurfaceNVector(lat, lon), toSun) > -0.05;
        }

        public static string Biome(CelestialBody b, double lat, double lon)
        {
            try { return ScienceUtil.GetExperimentBiome(b, lat, lon); } catch { return ""; }
        }

        public static string CompassName(double bearing)
        {
            string[] n = { "N", "NE", "E", "SE", "S", "SW", "W", "NW" };
            return n[(int)Math.Round(((bearing % 360) + 360) % 360 / 45.0) % 8];
        }
    }

    /// <summary>Deterministic hashing so the same territory always hosts the same species/fossils.</summary>
    public static class XenoHash
    {
        public static uint Hash(string s)
        {
            unchecked
            {
                uint h = 2166136261;
                for (int i = 0; i < s.Length; i++) { h ^= s[i]; h *= 16777619; }
                return h;
            }
        }

        public static uint Mix(uint a, int b)
        {
            unchecked
            {
                uint h = a ^ (uint)b * 0x9E3779B1u;
                h ^= h >> 16; h *= 0x85EBCA6Bu; h ^= h >> 13; h *= 0xC2B2AE35u; h ^= h >> 16;
                return h;
            }
        }

        public static float Unit(uint h) { return (h & 0xFFFFFF) / (float)0x1000000; }

        public static float Cell(string body, int cx, int cy, string what, int salt = 0)
        {
            uint h = Hash(body + "|" + what);
            h = Mix(h, cx); h = Mix(h, cy); h = Mix(h, salt);
            return Unit(h);
        }

        public static double CellSizeDeg(CelestialBody b)
        {
            return XenoSettings.TerritoryCellKm * 1000.0 / b.Radius * Geo.Rad2Deg;
        }
    }
}
