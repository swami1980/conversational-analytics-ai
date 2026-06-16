export interface LoginData {
  access_token: string
  token_type: string
  user: {
    role: string
    full_name: string
  }
}
