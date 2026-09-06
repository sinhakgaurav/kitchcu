import { useId, useState } from "react";
import {
  DEFAULT_COUNTRY,
  parsePhoneInput,
  type Country,
} from "../shared/validation";

type PhoneFieldProps = {
  label: string;
  /** National digits only — never includes the dial code. */
  value: string;
  /** Receives sanitized national digits, already capped at the national length. */
  onChange: (national: string) => void;
  onBlur?: () => void;
  error?: string;
  hint?: string;
  required?: boolean;
  disabled?: boolean;
  autoFocus?: boolean;
  autoComplete?: string;
  placeholder?: string;
  className?: string;
  country?: Country;
  name?: string;
};

/**
 * Mobile number entry with the country code fixed as an adornment.
 *
 * The user only ever types the national number, and the input is hard-capped at
 * the country's national length. A pasted `+91…`, `0091…`, `91…`, or leading
 * `0` is reduced to those digits; a pasted foreign country code is dropped and
 * explained rather than silently mangled.
 */
export function PhoneField({
  label,
  value,
  onChange,
  onBlur,
  error,
  hint,
  required,
  disabled,
  autoFocus,
  autoComplete = "tel",
  placeholder,
  className,
  country = DEFAULT_COUNTRY,
  name,
}: PhoneFieldProps) {
  const inputId = useId();
  const [dialNote, setDialNote] = useState<string | null>(null);

  const handleChange = (raw: string) => {
    const { national, foreignDial } = parsePhoneInput(raw, country);
    setDialNote(
      foreignDial
        ? `+${foreignDial} numbers are not supported yet — kitchCU serves India (+${country.dial}).`
        : null,
    );
    onChange(national);
  };

  const message = error || dialNote;
  const describedBy = message ? `${inputId}-msg` : hint ? `${inputId}-hint` : undefined;
  const remaining = country.nationalLength - value.length;

  return (
    <label className={className ? `phone-field ${className}` : "phone-field"} htmlFor={inputId}>
      <span className="phone-field__label">{label}</span>
      <span className={`phone-field__control${message ? " phone-field__control--invalid" : ""}`}>
        <span className="phone-field__dial" aria-hidden="true">
          {country.flag} +{country.dial}
        </span>
        <input
          id={inputId}
          name={name}
          className="phone-field__input"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onBlur={onBlur}
          onPaste={(e) => {
            // Let the parser see the whole pasted string, including a `+` prefix
            // the input would otherwise strip character by character.
            e.preventDefault();
            handleChange(e.clipboardData.getData("text"));
          }}
          type="tel"
          inputMode="numeric"
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          disabled={disabled}
          required={required}
          maxLength={country.nationalLength}
          placeholder={placeholder ?? country.example}
          aria-invalid={Boolean(message)}
          aria-describedby={describedBy}
        />
      </span>
      {message ? (
        <span className="field-error" id={`${inputId}-msg`} role="alert">
          {message}
        </span>
      ) : hint ? (
        <span className="field-hint" id={`${inputId}-hint`}>
          {hint}
        </span>
      ) : value.length > 0 && remaining > 0 ? (
        <span className="field-hint">
          {remaining} more digit{remaining === 1 ? "" : "s"}
        </span>
      ) : null}
    </label>
  );
}
