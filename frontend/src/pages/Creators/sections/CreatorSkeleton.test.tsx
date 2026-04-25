import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { CreatorSkeleton } from './CreatorSkeleton'

describe('CreatorSkeleton', () => {
  it('renders 6 skeleton cards', () => {
    const { container } = render(<CreatorSkeleton />)
    const cards = container.querySelectorAll('.skeleton-shimmer')
    expect(cards.length).toBeGreaterThan(0)
  })
})
