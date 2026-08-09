export interface GameProfile {
  game: string
  samples: Record<string, number>[]
}

export const gameProfiles: GameProfile[] = [
  {
    game: 'Free Fire',
    samples: [
      {
        aggression: 3,
        accuracy: 9,
        close_range_combat: 2,
        sniper_affinity: 9,
        rotation_timing: 6,
        teamwork: 5,
        risk_tolerance: 3,
        looting_focus: 7,
      },
      {
        aggression: 9,
        accuracy: 6,
        close_range_combat: 9,
        sniper_affinity: 2,
        rotation_timing: 3,
        teamwork: 4,
        risk_tolerance: 9,
        looting_focus: 2,
      },
      {
        aggression: 2,
        accuracy: 5,
        close_range_combat: 4,
        sniper_affinity: 3,
        rotation_timing: 7,
        teamwork: 10,
        risk_tolerance: 2,
        looting_focus: 6,
      },
    ],
  },
  {
    game: 'Arena of Valor',
    samples: [
      {
        aggression: 7,
        laning: 8,
        teamfighting: 6,
        objective_control: 7,
        map_awareness: 6,
        teamwork: 7,
        itemization: 8,
        mechanical_skill: 7,
      },
      {
        aggression: 5,
        laning: 4,
        teamfighting: 5,
        objective_control: 4,
        map_awareness: 5,
        teamwork: 5,
        itemization: 6,
        mechanical_skill: 5,
      },
    ],
  },
  {
    game: 'Speed Drifters',
    samples: [
      {
        cornering: 9,
        drafting: 6,
        drift_control: 8,
        boost_management: 7,
        consistency: 8,
        aggression: 5,
        track_knowledge: 7,
        risk_taking: 6,
      },
    ],
  },
  {
    game: 'Call of Duty: Mobile',
    samples: [
      {
        aggression: 8,
        accuracy: 7,
        close_range_combat: 8,
        long_range_accuracy: 5,
        map_control: 6,
        teamwork: 6,
        risk_tolerance: 7,
        reaction_time: 8,
      },
      {
        aggression: 4,
        accuracy: 5,
        close_range_combat: 4,
        long_range_accuracy: 6,
        map_control: 4,
        teamwork: 3,
        risk_tolerance: 4,
        reaction_time: 5,
      },
    ],
  },
  {
    game: 'Undawn',
    samples: [
      {
        resource_management: 8,
        combat_skill: 6,
        exploration_drive: 9,
        teamwork: 5,
        risk_tolerance: 4,
        stealth: 6,
        crafting: 8,
        endurance: 7,
      },
    ],
  },
]

export interface AveragedProfile {
  game: string
  metrics: { key: string; label: string; value: number }[]
}

function formatMetricKey(key: string): string {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function getPlayedGames(): string[] {
  return gameProfiles.map((profile) => profile.game)
}

export function getAveragedProfile(game: string): AveragedProfile | undefined {
  const profile = gameProfiles.find((p) => p.game === game)
  if (!profile) return undefined

  const keys = Object.keys(profile.samples[0])
  const metrics = keys.map((key) => {
    const sum = profile.samples.reduce((total, sample) => total + sample[key], 0)
    const value = Math.round((sum / profile.samples.length) * 10) / 10
    return { key, label: formatMetricKey(key), value }
  })

  return { game: profile.game, metrics }
}
