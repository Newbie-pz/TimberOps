export interface DashboardStats {
  vehicleCount: number
  totalNetWeightTons: string
  coalWeightTons: string
  oreWeightTons: string
  timberWeightTons: string
  overweightCount: number
  isMock: true
}

export async function getMockDashboardStats(): Promise<DashboardStats> {
  return {
    vehicleCount: 18,
    totalNetWeightTons: '426.580',
    coalWeightTons: '186.420',
    oreWeightTons: '142.760',
    timberWeightTons: '97.400',
    overweightCount: 3,
    isMock: true,
  }
}
