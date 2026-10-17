import { Badge, Button, Card, Progress, Slider } from '@ui-construction-library/core';
import {
  ActivityIcon,
  CheckIcon,
  ClockIcon,
  DollarSignIcon,
  SparklesIcon,
} from '@ui-construction-library/icons';
import { useEffect, useState } from 'react';
import { DEFAULT_SCHEDULE, PRO_PRICE_STARS } from './config';
import type { ScheduleSlot } from './types';
import { EmptyState } from './components/EmptyState';
import { ErrorBoundary } from './components/ErrorBoundary';

export function App() {
  const [workHours, setWorkHours] = useState(6);
  const [restHours, setRestHours] = useState(3);
  const [schedule, setSchedule] = useState<ScheduleSlot[]>(DEFAULT_SCHEDULE);
  const [isProModalOpen, setIsProModalOpen] = useState(false);
  const [purchasedPro, setPurchasedPro] = useState(false);

  const [newTime, setNewTime] = useState('14:00');
  const [newMessage, setNewMessage] = useState('');
  const [newCategory, setNewCategory] = useState<'work' | 'rest'>('work');
  const [newDuration] = useState(45);

  const ratio = restHours > 0 ? Number((workHours / restHours).toFixed(2)) : 9.99;
  const isOptimal = ratio >= 1.2 && ratio <= 2.5;

  useEffect(() => {
    // 1. Hydrate state from Telegram WebApp CloudStorage or localStorage
    const tg = (
      window as unknown as {
        Telegram?: {
          WebApp?: {
            CloudStorage?: {
              getItem?: (k: string, cb: (err: unknown, val: string) => void) => void;
              setItem?: (k: string, val: string) => void;
            };
          };
        };
      }
    ).Telegram?.WebApp;

    if (tg?.CloudStorage?.getItem) {
      tg.CloudStorage.getItem('ratio_schedule_state', (_err, val) => {
        if (val) {
          try {
            const parsed = JSON.parse(val);
            if (parsed.workHours) setWorkHours(parsed.workHours);
            if (parsed.restHours) setRestHours(parsed.restHours);
            if (parsed.schedule) setSchedule(parsed.schedule);
            if (parsed.purchasedPro) setPurchasedPro(parsed.purchasedPro);
          } catch (err) { console.error("[UDPA-Handled]", err);
            // Fallback
          }
        }
      });
    } else {
      const local = localStorage.getItem('ratio_schedule_state');
      if (local) {
        try {
          const parsed = JSON.parse(local);
          if (parsed.workHours) setWorkHours(parsed.workHours);
          if (parsed.restHours) setRestHours(parsed.restHours);
          if (parsed.schedule) setSchedule(parsed.schedule);
          if (parsed.purchasedPro) setPurchasedPro(parsed.purchasedPro);
        } catch (err) {
          console.warn('[Storage-Fallback]', err);
        }
      }
    }
  }, []);

  const saveState = (updated: {
    workHours?: number;
    restHours?: number;
    schedule?: ScheduleSlot[];
    purchasedPro?: boolean;
  }) => {
    const payload = JSON.stringify({
      workHours: updated.workHours ?? workHours,
      restHours: updated.restHours ?? restHours,
      schedule: updated.schedule ?? schedule,
      purchasedPro: updated.purchasedPro ?? purchasedPro,
    });
    localStorage.setItem('ratio_schedule_state', payload);
    const tg = (
      window as unknown as {
        Telegram?: {
          WebApp?: {
            CloudStorage?: {
              setItem?: (k: string, val: string) => void;
            };
          };
        };
      }
    ).Telegram?.WebApp;
    tg?.CloudStorage?.setItem?.('ratio_schedule_state', payload);
  };

  const toggleTask = (id: string) => {
    const updated = schedule.filter((item) => item.id !== id);
    setSchedule(updated);
    saveState({ schedule: updated });
  };

  const handleAddSlot = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim()) return;
    const newSlot: ScheduleSlot = {
      id: `slot_${Date.now()}`,
      time: newTime,
      message: newMessage.trim(),
      category: newCategory,
      durationMinutes: newDuration,
      buttonText: 'Выполнено',
    };
    const updated = [...schedule, newSlot].sort((a, b) => a.time.localeCompare(b.time));
    setSchedule(updated);
    saveState({ schedule: updated });
    setNewMessage('');
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-slate-950 text-slate-100 p-4 max-w-lg mx-auto font-sans">
      {/* Header */}
      <header className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <span>⚖️</span> Ratio & Schedule
          </h1>
          <p className="text-xs text-slate-400">Telegram Mini App Balance Manager</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setIsProModalOpen(true)}
          className="flex items-center gap-1 text-xs"
        >
          <SparklesIcon className="w-3.5 h-3.5 text-amber-400" />
          <span>{purchasedPro ? 'PRO Активен' : 'Stars PRO'}</span>
        </Button>
      </header>

      {/* Work/Rest Ratio Configurator Card */}
      <Card
        elevation="raised"
        className="bg-slate-900 border border-slate-800 rounded-2xl p-4 mb-6"
      >
        <div className="flex justify-between items-center mb-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Баланс дня (Work/Rest)
          </span>
          <Badge
            variant={isOptimal ? 'success' : 'warning'}
            className="text-xs font-bold px-2 py-0.5 rounded-full"
          >
            {ratio}:1 {isOptimal ? 'Гармония' : 'Дисбаланс'}
          </Badge>
        </div>

        <div className="space-y-4 mb-4">
          <div>
            <div className="flex justify-between text-xs text-slate-300 mb-1">
              <span>💼 Работа & Учеба:</span>
              <span className="font-bold">{workHours} ч.</span>
            </div>
            <Slider
              value={[workHours]}
              min={1}
              max={12}
              step={1}
              onChange={(val) => setWorkHours(val[0])}
            />
          </div>

          <div>
            <div className="flex justify-between text-xs text-slate-300 mb-1">
              <span>🎮 Отдых & Спорт:</span>
              <span className="font-bold">{restHours} ч.</span>
            </div>
            <Slider
              value={[restHours]}
              min={1}
              max={8}
              step={1}
              onChange={(val) => setRestHours(val[0])}
            />
          </div>
        </div>

        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800/80">
          <div className="flex justify-between text-[11px] text-slate-400 mb-1">
            <span>Продуктивность</span>
            <span>{Math.round((workHours / (workHours + restHours)) * 100)}%</span>
          </div>
          <Progress
            value={Math.round((workHours / (workHours + restHours)) * 100)}
            className="w-full bg-slate-800 h-2 rounded-full overflow-hidden"
          />
        </div>
      </Card>

      {/* Daily Schedule Timeline */}
      <section className="mb-6">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <ClockIcon className="w-4 h-4 text-sky-400" />
            <span>Расписание на сегодня ({schedule.length})</span>
          </h2>
        </div>

        {/* TimePicker Slot Creator */}
        <form
          onSubmit={handleAddSlot}
          className="bg-slate-900 border border-slate-800 rounded-xl p-3 mb-3 space-y-2.5"
        >
          <div className="flex justify-between items-center text-xs font-semibold text-slate-300">
            <span>⏰ Добавить активность:</span>
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => setNewCategory('work')}
                className={`text-[10px] px-2 py-0.5 rounded ${newCategory === 'work' ? 'bg-sky-500 text-white font-bold' : 'bg-slate-800 text-slate-400'}`}
              >
                Работа
              </button>
              <button
                type="button"
                onClick={() => setNewCategory('rest')}
                className={`text-[10px] px-2 py-0.5 rounded ${newCategory === 'rest' ? 'bg-emerald-500 text-white font-bold' : 'bg-slate-800 text-slate-400'}`}
              >
                Отдых
              </button>
            </div>
          </div>
          <div className="flex gap-2">
            <input
              type="time"
              value={newTime}
              onChange={(e) => setNewTime(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-sky-400 font-mono text-xs px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-sky-500"
              title="Time Picker"
            />
            <input
              type="text"
              placeholder="Название активности..."
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-800 text-slate-100 text-xs px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-sky-500 placeholder-slate-500"
            />
            <Button type="submit" size="sm" variant="default" className="text-xs font-bold px-3">
              +
            </Button>
          </div>
        </form>

        <div className="space-y-2.5">
          {schedule.length === 0 ? (
            <EmptyState
              onAction={() => setSchedule(DEFAULT_SCHEDULE)}
              actionText="Загрузить демо-план"
            />
          ) : (
            schedule.map((item) => (
            <Card
              key={item.id}
              elevation="flat"
              interactive
              className="bg-slate-900 border border-slate-800/80 rounded-xl p-3 flex items-center justify-between hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono font-bold text-sky-400 bg-sky-950/60 px-2 py-1 rounded-md border border-sky-800/40">
                  {item.time}
                </span>
                <div>
                  <div className="text-xs font-medium text-slate-200 line-clamp-1">
                    {item.message}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    {item.durationMinutes} мин • {item.category}
                  </div>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => toggleTask(item.id)}
                className="text-emerald-400 hover:text-white hover:bg-emerald-600/30 p-1.5 rounded-lg"
                title="Отметить выполненным"
              >
                <CheckIcon className="w-4 h-4" />
              </Button>
            </Card>
          )))}
        </div>
      </section>

      {/* Pro Modal for Telegram Stars */}
      {isProModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <Card
            elevation="overlay"
            className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-sm space-y-4"
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <SparklesIcon className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-bold text-white">Ratio & Schedule PRO</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsProModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Откройте неограниченный анализ привычек, синхронизацию с календарём и умные
              напоминания.
            </p>

            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 flex justify-between items-center text-xs">
              <span className="text-slate-400">Стоимость подписки:</span>
              <span className="font-bold text-amber-400 flex items-center gap-1">
                <DollarSignIcon className="w-3.5 h-3.5" />
                {PRO_PRICE_STARS} Telegram Stars
              </span>
            </div>

            <Button
              variant="default"
              onClick={() => {
                setPurchasedPro(true);
                setIsProModalOpen(false);
              }}
              className="w-full py-3 bg-amber-500 hover:bg-amber-400 text-black font-black text-xs uppercase tracking-wider rounded-xl transition-all shadow-md active:scale-98 flex items-center justify-center gap-1"
            >
              <ActivityIcon className="w-4 h-4" />
              <span>Оплатить {PRO_PRICE_STARS} Stars ⭐</span>
            </Button>
          </Card>
        </div>
      )}
      </div>
    </ErrorBoundary>
  );
}
