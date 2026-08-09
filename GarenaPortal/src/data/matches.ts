export type MatchResult = 'win' | 'loss'

export interface MatchStat {
  label: string
  value: string
}

export interface Match {
  id: string
  game: string
  mode: string
  map: string
  result: MatchResult
  score: string
  playedAt: string
  duration: string
  stats: MatchStat[]
}

export const recentMatches: Match[] = [
  {
    id: 'm1',
    game: 'Free Fire',
    mode: 'Battle Royale',
    map: 'Bermuda',
    result: 'win',
    score: '#1 · 7 kills',
    playedAt: '2026-08-09T14:12:00',
    duration: '18m 42s',
    stats: [
      { label: 'Placement', value: '#1 of 48' },
      { label: 'Kills', value: '7' },
      { label: 'Damage dealt', value: '1,842' },
      { label: 'Headshots', value: '3' },
      { label: 'Survival time', value: '18m 42s' },
    ],
  },
  {
    id: 'm2',
    game: 'Free Fire',
    mode: 'Clash Squad',
    map: 'Purgatory',
    result: 'loss',
    score: '4 - 7',
    playedAt: '2026-08-09T11:03:00',
    duration: '14m 05s',
    stats: [
      { label: 'Rounds', value: '4 - 7' },
      { label: 'Kills', value: '11' },
      { label: 'Deaths', value: '9' },
      { label: 'Assists', value: '3' },
      { label: 'Damage dealt', value: '2,150' },
    ],
  },
  {
    id: 'm3',
    game: 'Arena of Valor',
    mode: 'Ranked 5v5',
    map: 'Golden Trail',
    result: 'win',
    score: '2 - 0',
    playedAt: '2026-08-08T20:47:00',
    duration: '22m 18s',
    stats: [
      { label: 'Result', value: '2 - 0' },
      { label: 'Kills', value: '9' },
      { label: 'Deaths', value: '2' },
      { label: 'Assists', value: '12' },
      { label: 'Gold earned', value: '14,320' },
      { label: 'Damage to heroes', value: '38,240' },
    ],
  },
  {
    id: 'm4',
    game: 'Speed Drifters',
    mode: 'Time Trial',
    map: 'Neon Circuit',
    result: 'win',
    score: '1st · 1:42.318',
    playedAt: '2026-08-08T09:15:00',
    duration: '5m 04s',
    stats: [
      { label: 'Finish', value: '1st of 8' },
      { label: 'Best lap', value: '1:42.318' },
      { label: 'Top speed', value: '186 km/h' },
      { label: 'Drift score', value: '9,420' },
    ],
  },
  {
    id: 'm5',
    game: 'Free Fire',
    mode: 'Battle Royale',
    map: 'Kalahari',
    result: 'loss',
    score: '#14 · 2 kills',
    playedAt: '2026-08-07T22:30:00',
    duration: '9m 51s',
    stats: [
      { label: 'Placement', value: '#14 of 48' },
      { label: 'Kills', value: '2' },
      { label: 'Damage dealt', value: '612' },
      { label: 'Headshots', value: '1' },
      { label: 'Survival time', value: '9m 51s' },
    ],
  },
  {
    id: 'm6',
    game: 'Call of Duty: Mobile',
    mode: 'Team Deathmatch',
    map: 'Nuketown',
    result: 'win',
    score: '40 - 32',
    playedAt: '2026-08-06T19:20:00',
    duration: '9m 30s',
    stats: [
      { label: 'Score', value: '40 - 32' },
      { label: 'Kills', value: '22' },
      { label: 'Deaths', value: '14' },
      { label: 'Assists', value: '5' },
      { label: 'K/D ratio', value: '1.57' },
    ],
  },
  {
    id: 'm7',
    game: 'Undawn',
    mode: 'Survival Raid',
    map: 'Sunset Hollow',
    result: 'win',
    score: 'Cleared',
    playedAt: '2026-08-04T21:10:00',
    duration: '25m 00s',
    stats: [
      { label: 'Outcome', value: 'Cleared' },
      { label: 'Zombies defeated', value: '146' },
      { label: 'Resources gathered', value: '38' },
      { label: 'Damage taken', value: '212' },
    ],
  },
  {
    id: 'm8',
    game: 'Arena of Valor',
    mode: 'Ranked 5v5',
    map: 'Golden Trail',
    result: 'loss',
    score: '0 - 2',
    playedAt: '2026-08-03T18:05:00',
    duration: '19m 47s',
    stats: [
      { label: 'Result', value: '0 - 2' },
      { label: 'Kills', value: '3' },
      { label: 'Deaths', value: '7' },
      { label: 'Assists', value: '6' },
      { label: 'Gold earned', value: '9,140' },
      { label: 'Damage to heroes', value: '21,880' },
    ],
  },
  {
    id: 'm9',
    game: 'Call of Duty: Mobile',
    mode: 'Battle Royale',
    map: 'Isolated',
    result: 'loss',
    score: '#9 · 3 kills',
    playedAt: '2026-08-02T20:40:00',
    duration: '16m 10s',
    stats: [
      { label: 'Placement', value: '#9 of 60' },
      { label: 'Kills', value: '3' },
      { label: 'Damage dealt', value: '740' },
      { label: 'Survival time', value: '16m 10s' },
    ],
  },
]

export function getMatchById(id: string): Match | undefined {
  return recentMatches.find((match) => match.id === id)
}
