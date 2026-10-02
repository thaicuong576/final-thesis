import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { RouteErrorElement } from '../src/app/RouteErrorElement';

describe('RouteErrorElement', () => {
  it('renders Vietnamese error fallback when a route throws a runtime error', () => {
    function BombComponent(): ReactNode {
      throw new Error('u.limitations_vi.map is not a function');
    }

    const testRouter = createMemoryRouter(
      [
        {
          path: '/data',
          element: <BombComponent />,
          errorElement: <RouteErrorElement section="data" />,
        },
      ],
      { initialEntries: ['/data'] }
    );

    render(<RouterProvider router={testRouter} />);

    // Assert Vietnamese title and message
    expect(screen.getByText('Đã xảy ra sự cố khi tải trang dữ liệu')).toBeInTheDocument();
    expect(screen.getByText('u.limitations_vi.map is not a function')).toBeInTheDocument();

    // Assert link back to /analysis
    const backToAnalysis = screen.getByRole('link', { name: /Bàn làm việc phân tích/i });
    expect(backToAnalysis).toBeInTheDocument();
    expect(backToAnalysis).toHaveAttribute('href', '/analysis');

    // Assert no raw English developer texts like "Unexpected Application Error!"
    expect(screen.queryByText(/Unexpected Application Error/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Hey developer/i)).not.toBeInTheDocument();
  });

  it('renders analysis error fallback on /analysis route', () => {
    function BombAnalysis(): ReactNode {
      throw new Error('Analysis failed unexpectedly');
    }

    const testRouter = createMemoryRouter(
      [
        {
          path: '/analysis',
          element: <BombAnalysis />,
          errorElement: <RouteErrorElement section="analysis" />,
        },
      ],
      { initialEntries: ['/analysis'] }
    );

    render(<RouterProvider router={testRouter} />);

    expect(screen.getByText('Đã xảy ra sự cố trong quá trình phân tích')).toBeInTheDocument();
    expect(screen.getByText('Analysis failed unexpectedly')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Bàn làm việc phân tích/i })).toHaveAttribute('href', '/analysis');
  });
});
