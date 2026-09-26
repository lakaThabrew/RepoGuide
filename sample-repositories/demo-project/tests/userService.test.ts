import { userService } from '../src/services/userService'

describe('UserService', () => {
  // Reset store between tests by creating a fresh module scope
  beforeEach(() => {
    // Clear all users between tests
    const users = userService.list()
    users.forEach((u) => userService.remove(u.id))
  })

  describe('create', () => {
    it('creates a user and returns it with an id', () => {
      const user = userService.create({ name: 'Alice', email: 'alice@example.com' })
      expect(user.id).toBeDefined()
      expect(user.name).toBe('Alice')
      expect(user.email).toBe('alice@example.com')
      expect(user.createdAt).toBeDefined()
    })

    it('assigns unique ids to each user', () => {
      const a = userService.create({ name: 'Alice', email: 'alice@example.com' })
      const b = userService.create({ name: 'Bob', email: 'bob@example.com' })
      expect(a.id).not.toBe(b.id)
    })
  })

  describe('list', () => {
    it('returns an empty array when no users exist', () => {
      expect(userService.list()).toEqual([])
    })

    it('returns all created users', () => {
      userService.create({ name: 'Alice', email: 'alice@example.com' })
      userService.create({ name: 'Bob', email: 'bob@example.com' })
      expect(userService.list()).toHaveLength(2)
    })
  })

  describe('getById', () => {
    it('returns the user for a known id', () => {
      const user = userService.create({ name: 'Carol', email: 'carol@example.com' })
      expect(userService.getById(user.id)).toEqual(user)
    })

    it('returns undefined for an unknown id', () => {
      expect(userService.getById('does-not-exist')).toBeUndefined()
    })
  })

  describe('update', () => {
    it('updates fields and returns the updated user', () => {
      const user = userService.create({ name: 'Dave', email: 'dave@example.com' })
      const updated = userService.update(user.id, { name: 'David' })
      expect(updated?.name).toBe('David')
      expect(updated?.email).toBe('dave@example.com')
    })

    it('returns undefined when user does not exist', () => {
      expect(userService.update('no-such-id', { name: 'X' })).toBeUndefined()
    })
  })

  describe('remove', () => {
    it('removes a user and returns true', () => {
      const user = userService.create({ name: 'Eve', email: 'eve@example.com' })
      expect(userService.remove(user.id)).toBe(true)
      expect(userService.getById(user.id)).toBeUndefined()
    })

    it('returns false when user does not exist', () => {
      expect(userService.remove('ghost')).toBe(false)
    })
  })
})
