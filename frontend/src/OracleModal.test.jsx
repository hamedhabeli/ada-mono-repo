// src/OracleModal.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import OracleModal from './OracleModal';

describe('OracleModal Component', () => {
  it('should not render when isOpen is false', () => {
    const { container } = render(<OracleModal isOpen={false} unsatCore={[]} onSubmit={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('should render deadlock message and unsat core when open', () => {
    render(<OracleModal isOpen={true} unsatCore={['C_1', 'C_2']} onSubmit={() => {}} />);
    
    expect(screen.getByText(/Gödelian Deadlock/i)).toBeDefined();
    expect(screen.getByText(/C_1 AND C_2/i)).toBeDefined();
  });

  it('should call onSubmit with the new axiom when button is clicked', () => {
    const mockSubmit = vi.fn();
    render(<OracleModal isOpen={true} unsatCore={['C_1']} onSubmit={mockSubmit} />);
    
    const input = screen.getByPlaceholderText(/Enter a new Meta-Axiom/i);
    const button = screen.getByText(/Inject Axiom/i);
    
    fireEvent.change(input, { target: { value: 'x can be negative' } });
    fireEvent.click(button);
    
    expect(mockSubmit).toHaveBeenCalledWith('x can be negative');
  });
});