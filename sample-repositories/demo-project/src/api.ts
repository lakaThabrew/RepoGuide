import axios, { AxiosInstance } from 'axios'

export interface User {
  id: string
  name: string
  email: string
  createdAt: string
}

export interface CreateUserPayload {
  name: string
  email: string
}

export interface UpdateUserPayload {
  name?: string
  email?: string
}

/**
 * Typed HTTP client for the demo-project API.
 *
 * Usage:
 *   const client = createApiClient('http://localhost:3001')
 *   const users = await client.listUsers()
 */
export function createApiClient(baseURL: string) {
  const http: AxiosInstance = axios.create({ baseURL })

  return {
    listUsers: (): Promise<User[]> =>
      http.get<User[]>('/users').then((r) => r.data),

    getUser: (id: string): Promise<User> =>
      http.get<User>(`/users/${id}`).then((r) => r.data),

    createUser: (payload: CreateUserPayload): Promise<User> =>
      http.post<User>('/users', payload).then((r) => r.data),

    updateUser: (id: string, payload: UpdateUserPayload): Promise<User> =>
      http.put<User>(`/users/${id}`, payload).then((r) => r.data),

    deleteUser: (id: string): Promise<void> =>
      http.delete(`/users/${id}`).then(() => undefined),
  }
}
