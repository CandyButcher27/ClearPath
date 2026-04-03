export interface LogLine {
  timestamp: string
  level: 'SYSTEM' | 'INFO' | 'OK' | 'WARN' | 'HASH'
  message: string
}

export interface FlagResult {
  is_flagged: boolean
  [key: string]: unknown
}

export interface VerificationResults {
  product_id?: string
  category_metadata?: {
    applied_category?: string
    fields?: Record<string, unknown>
  }
  normalized_aggregates?: {
    total_weight_reported_kg?: number
    total_package_count?: number
    ship_to_address_standardized?: string
    total_value?: number
    currency?: string
  }
  inconsistency_flags?: {
    logistics_flags?: Record<string, FlagResult | null>
    quantity_weight_flags?: Record<string, FlagResult | null>
    product_specific_flags?: Record<string, FlagResult | null>
    financial_timing_flags?: Record<string, FlagResult | null>
  }
}

export interface CompleteEvent {
  results: VerificationResults | null
  error: string | null
  status: string
}
