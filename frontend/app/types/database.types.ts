export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.1"
  }
  public: {
    Tables: {
      canonical_product_drafts: {
        Row: {
          created_at: string
          id: string
          llm_reasoning: string | null
          reviewed_at: string | null
          source_item_ids: string[]
          status: string
          suggested_category: string | null
          suggested_name: string
          suggested_short_name: string | null
        }
        Insert: {
          created_at?: string
          id?: string
          llm_reasoning?: string | null
          reviewed_at?: string | null
          source_item_ids: string[]
          status?: string
          suggested_category?: string | null
          suggested_name: string
          suggested_short_name?: string | null
        }
        Update: {
          created_at?: string
          id?: string
          llm_reasoning?: string | null
          reviewed_at?: string | null
          source_item_ids?: string[]
          status?: string
          suggested_category?: string | null
          suggested_name?: string
          suggested_short_name?: string | null
        }
        Relationships: []
      }
      canonical_products: {
        Row: {
          barcode: string | null
          category_id: string | null
          created_at: string
          embedding: string | null
          id: string
          name: string
          short_name: string
          unit_id: string | null
          updated_at: string
        }
        Insert: {
          barcode?: string | null
          category_id?: string | null
          created_at?: string
          embedding?: string | null
          id?: string
          name: string
          short_name: string
          unit_id?: string | null
          updated_at?: string
        }
        Update: {
          barcode?: string | null
          category_id?: string | null
          created_at?: string
          embedding?: string | null
          id?: string
          name?: string
          short_name?: string
          unit_id?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "canonical_products_category_id_fkey"
            columns: ["category_id"]
            isOneToOne: false
            referencedRelation: "categories"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "canonical_products_unit_id_fkey"
            columns: ["unit_id"]
            isOneToOne: false
            referencedRelation: "units"
            referencedColumns: ["id"]
          },
        ]
      }
      categories: {
        Row: {
          id: string
          name: string
          parent_id: string | null
        }
        Insert: {
          id?: string
          name: string
          parent_id?: string | null
        }
        Update: {
          id?: string
          name?: string
          parent_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "categories_parent_id_fkey"
            columns: ["parent_id"]
            isOneToOne: false
            referencedRelation: "categories"
            referencedColumns: ["id"]
          },
        ]
      }
      product_matches: {
        Row: {
          canonical_product_id: string | null
          confidence: number
          created_at: string
          id: string
          matched_by: string | null
          receipt_item_id: string
          reviewed_at: string | null
          status: Database["public"]["Enums"]["match_status"]
        }
        Insert: {
          canonical_product_id?: string | null
          confidence: number
          created_at?: string
          id?: string
          matched_by?: string | null
          receipt_item_id: string
          reviewed_at?: string | null
          status?: Database["public"]["Enums"]["match_status"]
        }
        Update: {
          canonical_product_id?: string | null
          confidence?: number
          created_at?: string
          id?: string
          matched_by?: string | null
          receipt_item_id?: string
          reviewed_at?: string | null
          status?: Database["public"]["Enums"]["match_status"]
        }
        Relationships: [
          {
            foreignKeyName: "product_matches_canonical_product_id_fkey"
            columns: ["canonical_product_id"]
            isOneToOne: false
            referencedRelation: "canonical_products"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "product_matches_receipt_item_id_fkey"
            columns: ["receipt_item_id"]
            isOneToOne: true
            referencedRelation: "receipt_items"
            referencedColumns: ["id"]
          },
        ]
      }
      receipt_items: {
        Row: {
          canonical_product_id: string | null
          created_at: string
          discount: number | null
          id: string
          ignore: boolean | null
          quantity: number
          raw_name: string
          receipt_id: string
          short_name: string | null
          tax_rate: number | null
          total_price: number
          unit_id: string | null
          unit_price: number
          user_id: string
        }
        Insert: {
          canonical_product_id?: string | null
          created_at?: string
          discount?: number | null
          id?: string
          ignore?: boolean | null
          quantity: number
          raw_name: string
          receipt_id: string
          short_name?: string | null
          tax_rate?: number | null
          total_price: number
          unit_id?: string | null
          unit_price: number
          user_id: string
        }
        Update: {
          canonical_product_id?: string | null
          created_at?: string
          discount?: number | null
          id?: string
          ignore?: boolean | null
          quantity?: number
          raw_name?: string
          receipt_id?: string
          short_name?: string | null
          tax_rate?: number | null
          total_price?: number
          unit_id?: string | null
          unit_price?: number
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "receipt_items_canonical_product_id_fkey"
            columns: ["canonical_product_id"]
            isOneToOne: false
            referencedRelation: "canonical_products"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "receipt_items_receipt_id_fkey"
            columns: ["receipt_id"]
            isOneToOne: false
            referencedRelation: "receipts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "receipt_items_unit_id_fkey"
            columns: ["unit_id"]
            isOneToOne: false
            referencedRelation: "units"
            referencedColumns: ["id"]
          },
        ]
      }
      receipt_sources: {
        Row: {
          created_at: string
          external_id: string | null
          id: string
          pdf_urls: string[] | null
          raw_html: string | null
          raw_text: string | null
          receipt_id: string | null
          source_type: string
          user_id: string
        }
        Insert: {
          created_at?: string
          external_id?: string | null
          id?: string
          pdf_urls?: string[] | null
          raw_html?: string | null
          raw_text?: string | null
          receipt_id?: string | null
          source_type: string
          user_id: string
        }
        Update: {
          created_at?: string
          external_id?: string | null
          id?: string
          pdf_urls?: string[] | null
          raw_html?: string | null
          raw_text?: string | null
          receipt_id?: string | null
          source_type?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "receipt_sources_receipt_id_fkey"
            columns: ["receipt_id"]
            isOneToOne: false
            referencedRelation: "receipts"
            referencedColumns: ["id"]
          },
        ]
      }
      receipts: {
        Row: {
          created_at: string
          currency: string
          id: string
          payment_method: string | null
          purchased_at: string
          store_id: string | null
          subtotal: number | null
          tax_total: number | null
          total: number
          user_id: string
        }
        Insert: {
          created_at?: string
          currency?: string
          id?: string
          payment_method?: string | null
          purchased_at: string
          store_id?: string | null
          subtotal?: number | null
          tax_total?: number | null
          total: number
          user_id: string
        }
        Update: {
          created_at?: string
          currency?: string
          id?: string
          payment_method?: string | null
          purchased_at?: string
          store_id?: string | null
          subtotal?: number | null
          tax_total?: number | null
          total?: number
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "receipts_store_id_fkey"
            columns: ["store_id"]
            isOneToOne: false
            referencedRelation: "stores"
            referencedColumns: ["id"]
          },
        ]
      }
      store_chains: {
        Row: {
          country: string
          id: string
          logo_url: string | null
          name: string
        }
        Insert: {
          country?: string
          id?: string
          logo_url?: string | null
          name: string
        }
        Update: {
          country?: string
          id?: string
          logo_url?: string | null
          name?: string
        }
        Relationships: []
      }
      stores: {
        Row: {
          address: string | null
          chain_id: string | null
          city: string | null
          country: string
          created_at: string
          id: string
          ignore: boolean | null
          name: string
          postal_code: string | null
          user_id: string
        }
        Insert: {
          address?: string | null
          chain_id?: string | null
          city?: string | null
          country?: string
          created_at?: string
          id?: string
          ignore?: boolean | null
          name: string
          postal_code?: string | null
          user_id: string
        }
        Update: {
          address?: string | null
          chain_id?: string | null
          city?: string | null
          country?: string
          created_at?: string
          id?: string
          ignore?: boolean | null
          name?: string
          postal_code?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "stores_chain_id_fkey"
            columns: ["chain_id"]
            isOneToOne: false
            referencedRelation: "store_chains"
            referencedColumns: ["id"]
          },
        ]
      }
      units: {
        Row: {
          id: string
          name: string
          quantity: string
          symbol: string
        }
        Insert: {
          id?: string
          name: string
          quantity: string
          symbol: string
        }
        Update: {
          id?: string
          name?: string
          quantity?: string
          symbol?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      show_limit: { Args: never; Returns: number }
      show_trgm: { Args: { "": string }; Returns: string[] }
    }
    Enums: {
      match_status: "pending" | "confirmed" | "rejected"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      match_status: ["pending", "confirmed", "rejected"],
    },
  },
} as const
