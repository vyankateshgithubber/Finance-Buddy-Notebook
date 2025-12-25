import axios from 'axios'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://finance-buddy-notebook.onrender.com'

export const api = axios.create({
  baseURL: "https://finance-buddy-notebook.onrender.com",
})
