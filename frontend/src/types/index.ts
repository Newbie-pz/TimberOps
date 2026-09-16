export type Tons = string

export type CargoType = 'ORE' | 'COAL' | 'TIMBER' | 'OTHER'
export type WeighingDirection = 'OUTBOUND' | 'INBOUND'
export type WeighingStatus =
  | 'WAIT_TARE'
  | 'TARE_COMPLETED'
  | 'WAIT_GROSS'
  | 'GROSS_COMPLETED'
  | 'COMPLETED'
  | 'CANCELLED'
export type WeightResult = 'PENDING' | 'NORMAL' | 'OVERWEIGHT'
export type WeightType = 'TARE' | 'GROSS' | 'REWEIGH'
export type WeightSource = 'MANUAL' | 'DEVICE'

export interface Vehicle {
  id: string
  plate_number: string
  driver_name: string | null
  driver_phone: string | null
  vehicle_type: string | null
  allowed_gross_weight_tons: Tons
  remark: string | null
  created_at: string
  updated_at: string
}

export interface VehicleCreate {
  plate_number: string
  driver_name?: string | null
  driver_phone?: string | null
  vehicle_type?: string | null
  allowed_gross_weight_tons: Tons
  remark?: string | null
}

export type VehicleUpdate = Omit<VehicleCreate, 'plate_number'>

export interface Customer {
  id: string
  name: string
  contact_name: string | null
  phone: string | null
  remark: string | null
  created_at: string
  updated_at: string
}

export interface CustomerCreate {
  name: string
  contact_name?: string | null
  phone?: string | null
  remark?: string | null
}

export type CustomerUpdate = Partial<CustomerCreate>

export interface WeighingTask {
  id: string
  task_no: string
  vehicle_id: string
  customer_id: string | null
  weighing_direction: WeighingDirection
  cargo_type: CargoType
  cargo_name: string | null
  cargo_remark: string | null
  driver_name_snapshot: string | null
  driver_phone_snapshot: string | null
  tare_weight_tons: Tons | null
  gross_weight_tons: Tons | null
  net_weight_tons: Tons | null
  allowed_gross_weight_tons: Tons
  overweight_tons: Tons
  status: WeighingStatus
  weight_result: WeightResult
  tare_time: string | null
  gross_time: string | null
  completed_at: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface WeighingTaskCreate {
  vehicle_id: string
  customer_id?: string | null
  weighing_direction: WeighingDirection
  cargo_type: CargoType
  cargo_name?: string | null
  cargo_remark?: string | null
}

export interface WeighingRecord {
  id: string
  weighing_task_id: string
  weight_type: WeightType
  weight_tons: Tons
  sequence_no: number
  recorded_at: string
  recorded_by: string | null
  source: WeightSource
  remark: string | null
  created_at: string
}

export interface TaskDetailResponse {
  task: WeighingTask
  records: WeighingRecord[]
}

export interface WeighingTaskFilters {
  cargo_type?: CargoType
  status?: WeighingStatus
  vehicle_id?: string
}

export type CargoCatalog = Record<CargoType, string[]>

export interface WeighingExportFilters {
  start_date?: string
  end_date?: string
  vehicle_id?: string
  customer_id?: string
  cargo_type?: CargoType
}

export interface WeighingExportFile {
  blob: Blob
  filename: string
}

export interface WeightInput {
  weight_tons: Tons
  remark?: string | null
}

export interface ReweighInput {
  weight_tons: Tons
  remark: string
}

export interface AIToolCall {
  name: string
  arguments: Record<string, unknown>
  status: string
}

export interface AIChatRequest {
  message: string
}

export interface AIChatResponse {
  answer: string
  tool_calls: AIToolCall[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: AIToolCall[]
  createdAt: string
}
