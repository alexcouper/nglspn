"use client";

import { EntityIcon } from "./EntityIcon";

export interface Choice {
  id: string;
  title: string;
  subtitle?: string;
  imageUrl?: string | null;
}

interface ChoiceListProps {
  /** Radio group name. Distinct per dialog so two open lists can't share state. */
  name: string;
  choices: Choice[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const ICON_SIZE = 40;

/** Pick one of a list of things, each shown with an image, a title and a line
 *  underneath. Shared by the entry dialogs so they look alike — which is the
 *  whole reason it exists, and why it knows nothing about competitions or
 *  projects. Callers map their own data into `Choice[]`. */
export function ChoiceList({
  name,
  choices,
  selectedId,
  onSelect,
}: ChoiceListProps) {
  if (choices.length === 0) return null;

  // One choice is not a choice: a radio that cannot be operated is a control
  // that only asks to be clicked. The caller has it selected already.
  const chooseable = choices.length > 1;

  return (
    <ul role={chooseable ? "radiogroup" : "list"} className="divide-y divide-border">
      {choices.map((choice) => {
        const row = (
          <>
            {chooseable && (
              <input
                type="radio"
                name={name}
                value={choice.id}
                checked={selectedId === choice.id}
                onChange={() => onSelect(choice.id)}
                className="flex-shrink-0"
              />
            )}
            <EntityIcon
              imageUrl={choice.imageUrl}
              title={choice.title}
              size={ICON_SIZE}
            />
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {choice.title}
              </p>
              {choice.subtitle && (
                <p className="text-xs text-muted-foreground truncate mt-0.5">
                  {choice.subtitle}
                </p>
              )}
            </div>
          </>
        );

        return (
          <li key={choice.id}>
            {chooseable ? (
              <label className="flex items-center gap-3 py-3 cursor-pointer">
                {row}
              </label>
            ) : (
              <div className="flex items-center gap-3 py-3">{row}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
