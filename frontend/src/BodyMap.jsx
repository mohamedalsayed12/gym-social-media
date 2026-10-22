const REGIONS = ["shoulders", "chest", "back", "arms", "core", "legs"];

function tone(percent) {
  if (!percent) return "#24272e";
  const alpha = 0.22 + (percent / 100) * 0.78;
  return `rgba(198, 241, 53, ${alpha})`;
}

export default function BodyMap({ hits = [] }) {
  const byRegion = Object.fromEntries(hits.map((hit) => [hit.muscle_group, hit.percent]));
  const fill = (region) => tone(byRegion[region] || 0);

  return (
    <div className="body-map">
      <svg viewBox="0 0 200 430" role="img" aria-label="Body muscle split this week">
        <circle cx="100" cy="36" r="24" fill="#2a2d34" />
        <rect x="88" y="58" width="24" height="18" rx="6" fill="#2a2d34" />
        <path d="M58 92 Q100 78 142 92 L150 118 Q100 108 50 118 Z" fill={fill("shoulders")} />
        <path d="M68 112 H132 Q136 150 128 168 H72 Q64 150 68 112 Z" fill={fill("chest")} />
        <path d="M74 172 H126 L120 230 H80 Z" fill={fill("core")} />
        <path d="M46 116 Q28 150 34 210 Q48 214 54 180 L62 124 Z" fill={fill("arms")} />
        <path d="M154 116 Q172 150 166 210 Q152 214 146 180 L138 124 Z" fill={fill("arms")} />
        <path d="M78 236 H98 L92 390 Q84 400 76 390 L70 250 Z" fill={fill("legs")} />
        <path d="M102 236 H122 L130 250 L124 390 Q116 400 108 390 Z" fill={fill("legs")} />
        <path d="M70 118 H130 L124 150 H76 Z" fill={fill("back")} opacity="0.55" />
      </svg>
      <ul>
        {REGIONS.map((region) => (
          <li key={region}>
            <span className="swatch" style={{ background: fill(region) }} />
            <span>{region}</span>
            <strong>{byRegion[region] || 0}%</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}
