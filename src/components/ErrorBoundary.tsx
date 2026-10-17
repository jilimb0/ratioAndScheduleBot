import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary-Caught]', error, errorInfo);
  }

  public override render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="p-6 text-center rounded-xl bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800">
            <h2 className="text-lg font-bold text-red-600 dark:text-red-400 mb-2">
              Что-то пошло не так
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
              {this.state.error?.message || 'Произошла непредвиденная ошибка в интерфейсе.'}
            </p>
            <button
              type="button"
              onClick={() => this.setState({ hasError: false })}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm transition"
            >
              Попробовать снова
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
