"use client";

import { useRef, useState, useEffect, KeyboardEvent, ClipboardEvent } from "react";

interface PinInputProps {
  onComplete: (code: string) => void;
  disabled?: boolean;
  hasError?: boolean;
}

export function PinInput({ onComplete, disabled = false, hasError = false }: PinInputProps) {
  const [values, setValues] = useState<string[]>(["", "", "", "", "", ""]);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const handleChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, "").slice(-1);

    const newValues = [...values];
    newValues[index] = digit;
    setValues(newValues);

    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    if (digit && index === 5) {
      const code = newValues.join("");
      if (code.length === 6) {
        onComplete(code);
      }
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !values[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);

    if (pastedData.length > 0) {
      const newValues = [...values];
      for (let i = 0; i < 6; i++) {
        newValues[i] = pastedData[i] || "";
      }
      setValues(newValues);

      const nextEmptyIndex = newValues.findIndex((v) => !v);
      if (nextEmptyIndex !== -1) {
        inputRefs.current[nextEmptyIndex]?.focus();
      } else {
        inputRefs.current[5]?.focus();
        onComplete(newValues.join(""));
      }
    }
  };

  return (
    <div className="flex gap-2 justify-center">
      {values.map((value, index) => (
        <input
          key={index}
          ref={(el) => {
            inputRefs.current[index] = el;
          }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={value}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          onPaste={handlePaste}
          disabled={disabled}
          className={`w-11 h-12 text-center text-xl font-medium rounded-lg border transition-colors
            focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/12
            ${hasError ? "border-red-300 bg-red-50" : "border-border"}
            ${disabled ? "opacity-50 cursor-not-allowed bg-muted" : "bg-white"}
          `}
        />
      ))}
    </div>
  );
}
