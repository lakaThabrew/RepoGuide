import { randomUUID } from 'crypto'

export interface User {
  id: string
  name: string
  email: string
  createdAt: string
}

type UserInput = Omit<User, 'id' | 'createdAt'>
type UserPatch = Partial<UserInput>

/**
 * In-memory user store.
 *
 * In a production application this would be backed by a database.
 * For this demo it uses a plain Map so there are no external dependencies.
 */
class UserService {
  private store = new Map<string, User>()

  list(): User[] {
    return Array.from(this.store.values())
  }

  getById(id: string): User | undefined {
    return this.store.get(id)
  }

  create(input: UserInput): User {
    const user: User = {
      id: randomUUID(),
      name: input.name,
      email: input.email,
      createdAt: new Date().toISOString(),
    }
    this.store.set(user.id, user)
    return user
  }

  update(id: string, patch: UserPatch): User | undefined {
    const existing = this.store.get(id)
    if (!existing) return undefined
    const updated: User = { ...existing, ...patch }
    this.store.set(id, updated)
    return updated
  }

  remove(id: string): boolean {
    return this.store.delete(id)
  }
}

export const userService = new UserService()
