/**
 * Shared form validation — phone, name, email, and the small text rules that
 * every kitchCU form needs.
 *
 * Phone entry is deliberately narrow: the country code is never typed by the
 * user. The field shows the dial code as a fixed adornment and accepts exactly
 * the national length (10 digits in India). Anything a user pastes — `+91…`,
 * `0091…`, `91…`, or a leading trunk `0` — is reduced to those national digits
 * so the visible field can stay strictly capped.
 */

export type Country = {
  iso2: string;
  /** Dial code without the `+`. */
  dial: string;
  name: string;
  flag: string;
  /** Exact number of national digits — the hard cap on the input. */
  nationalLength: number;
  /** Full-match pattern for a valid mobile in national form. */
  mobilePattern: RegExp;
  /** Shown as the input placeholder. */
  example: string;
};

/**
 * kitchCU serves India only: OTP delivery, kitchen onboarding, and payments are
 * all India-bound. The table exists so adding a market later is a data change
 * rather than a rewrite — it is not a promise that other dial codes work.
 */
export const INDIA: Country = {
  iso2: "IN",
  dial: "91",
  name: "India",
  flag: "🇮🇳",
  nationalLength: 10,
  mobilePattern: /^[6-9]\d{9}$/,
  example: "9876543210",
};

export const SUPPORTED_COUNTRIES: readonly Country[] = [INDIA];
export const DEFAULT_COUNTRY = INDIA;

/** Dial codes we can recognise well enough to reject with a useful message. */
const KNOWN_FOREIGN_DIALS = [
  "1",
  "44",
  "61",
  "65",
  "971",
  "966",
  "974",
  "968",
  "973",
  "60",
  "94",
  "977",
  "880",
  "92",
];

export type PhoneParts = {
  /** National digits, capped at the country's national length. */
  national: string;
  country: Country;
  /** Set when the input carried an explicit country code we do not serve. */
  foreignDial: string | null;
};

function digitsOnly(value: string): string {
  return (value || "").replace(/\D/g, "");
}

/**
 * Reduce any raw phone input to national digits for `country`.
 *
 * Handles the four ways people paste an Indian mobile — bare 10 digits,
 * `+91`/`91` prefixed, `0091` IDD, and a leading trunk `0` — and flags an
 * explicit foreign dial code so the caller can explain why it is rejected.
 */
export function parsePhoneInput(raw: string, country: Country = DEFAULT_COUNTRY): PhoneParts {
  const trimmed = (raw || "").trim();
  const explicitIntl = trimmed.startsWith("+") || /^00\d/.test(digitsOnly(trimmed));
  let digits = digitsOnly(trimmed);

  // `0091…` is the same intent as `+91…`.
  if (digits.startsWith("00")) digits = digits.slice(2);

  const { dial, nationalLength } = country;

  // Our own dial code, with the full national number behind it.
  if (digits.startsWith(dial) && digits.length === dial.length + nationalLength) {
    return { national: digits.slice(dial.length), country, foreignDial: null };
  }

  // Domestic trunk prefix: 0 followed by the full national number.
  if (digits.startsWith("0") && digits.length === nationalLength + 1) {
    return { national: digits.slice(1), country, foreignDial: null };
  }

  // Only treat this as a foreign number when the user actually wrote a `+`
  // or `00` — otherwise a half-typed local number would look foreign.
  if (explicitIntl && !digits.startsWith(dial)) {
    const foreign = KNOWN_FOREIGN_DIALS.find((code) => digits.startsWith(code));
    if (foreign) {
      return { national: digits.slice(foreign.length, foreign.length + nationalLength), country, foreignDial: foreign };
    }
    if (digits.length > nationalLength) {
      return { national: digits.slice(-nationalLength), country, foreignDial: digits.slice(0, digits.length - nationalLength) };
    }
  }

  return { national: digits.slice(0, nationalLength), country, foreignDial: null };
}

/**
 * Sanitized value for a controlled phone input — strips separators and any
 * pasted country code, then caps at the national length so the field can never
 * hold more than 10 digits.
 */
export function phoneInputValue(raw: string, country: Country = DEFAULT_COUNTRY): string {
  return parsePhoneInput(raw, country).national;
}

/** Validate national digits. Returns an error message, or null when valid. */
export function validateNationalPhone(
  national: string,
  country: Country = DEFAULT_COUNTRY,
  { required = true }: { required?: boolean } = {},
): string | null {
  const digits = digitsOnly(national);
  if (!digits) return required ? "Enter your mobile number" : null;
  if (digits.length < country.nationalLength) {
    return `Enter all ${country.nationalLength} digits`;
  }
  if (!country.mobilePattern.test(digits)) {
    return country.iso2 === "IN"
      ? "Indian mobile numbers start with 6, 7, 8, or 9"
      : `Enter a valid ${country.name} mobile number`;
  }
  return null;
}

/** National digits + country → E.164. Assumes the digits already validated. */
export function toE164(national: string, country: Country = DEFAULT_COUNTRY): string {
  return `+${country.dial}${digitsOnly(national)}`;
}

/**
 * Full-string phone normalization for callers that hold a raw value rather
 * than a `PhoneField`. Throws with a user-facing message.
 */
export function normalizePhone(phone: string, country: Country = DEFAULT_COUNTRY): string {
  const parts = parsePhoneInput(phone, country);
  if (parts.foreignDial) {
    throw new Error(`kitchCU currently serves India only — use a +${country.dial} mobile number`);
  }
  const error = validateNationalPhone(parts.national, country);
  if (error) throw new Error(error);
  return toE164(parts.national, country);
}

/** Format for display: `+91 98765 43210`. */
export function formatPhoneDisplay(value: string, country: Country = DEFAULT_COUNTRY): string {
  const { national } = parsePhoneInput(value, country);
  if (national.length !== country.nationalLength) return value;
  return `+${country.dial} ${national.slice(0, 5)} ${national.slice(5)}`;
}

// ------------------------------------------------------------------ name / email

/**
 * Letters, combining marks, and the punctuation real names contain.
 * `\p{M}` is essential: Indic scripts write vowels as combining matras, so
 * `\p{L}` alone rejects ordinary Hindi, Marathi, Tamil, and Bengali names.
 */
const NAME_PATTERN = /^[\p{L}\p{M}.\-'’\s]+$/u;

/** Validate a person's display name. Returns an error message, or null. */
export function validatePersonName(
  name: string,
  { required = true }: { required?: boolean } = {},
): string | null {
  const cleaned = (name || "").trim();
  if (!cleaned) return required ? "Enter your name" : null;
  if (cleaned.length < 2) return "Name must be at least 2 characters";
  if (cleaned.length > 120) return "Name must be under 120 characters";
  if (/\d/.test(cleaned)) return "Name must not contain digits";
  if (!NAME_PATTERN.test(cleaned)) {
    return "Name may only contain letters, spaces, apostrophes, hyphens, or dots";
  }
  return null;
}

export function normalizePersonName(name: string): string {
  const error = validatePersonName(name);
  if (error) throw new Error(error);
  return name.trim();
}

// Deliberately stricter than the HTML5 default: requires a dot-separated TLD so
// `a@b` (which browsers accept) does not reach the API.
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i;

export function validateEmail(
  email: string,
  { required = true }: { required?: boolean } = {},
): string | null {
  const cleaned = (email || "").trim();
  if (!cleaned) return required ? "Enter your email address" : null;
  if (cleaned.length > 254) return "Email must be under 254 characters";
  if (!EMAIL_PATTERN.test(cleaned)) return "Enter a valid email address, like name@example.com";
  return null;
}

export function normalizeEmail(email: string): string {
  const error = validateEmail(email);
  if (error) throw new Error(error);
  return email.trim().toLowerCase();
}

// ----------------------------------------------------------------- small fields

/** OTP is always 6 numeric digits. */
export function validateOtp(otp: string): string | null {
  const digits = digitsOnly(otp);
  if (!digits) return "Enter the 6-digit code";
  if (digits.length !== 6) return "The code is 6 digits";
  return null;
}

export function otpInputValue(raw: string): string {
  return digitsOnly(raw).slice(0, 6);
}

/** India PIN code — 6 digits, never starting with 0. */
export function validatePincode(
  pincode: string,
  { required = true }: { required?: boolean } = {},
): string | null {
  const digits = digitsOnly(pincode);
  if (!digits) return required ? "Enter the PIN code" : null;
  if (!/^[1-9]\d{5}$/.test(digits)) return "Enter a valid 6-digit PIN code";
  return null;
}

export function pincodeInputValue(raw: string): string {
  return digitsOnly(raw).slice(0, 6);
}

/** Free text with a length window — used for notes, subjects, addresses. */
export function validateText(
  value: string,
  label: string,
  { required = true, min = 1, max = 500 }: { required?: boolean; min?: number; max?: number } = {},
): string | null {
  const cleaned = (value || "").trim();
  if (!cleaned) return required ? `Enter ${label}` : null;
  if (cleaned.length < min) return `${label} must be at least ${min} characters`;
  if (cleaned.length > max) return `${label} must be under ${max} characters`;
  return null;
}

/** Collapse a field-error map to the first message, for the form-level banner. */
export function firstError(errors: Record<string, string | undefined>): string | null {
  for (const value of Object.values(errors)) {
    if (value) return value;
  }
  return null;
}

/** True when every entry in the map is empty. */
export function isClean(errors: Record<string, string | undefined>): boolean {
  return firstError(errors) === null;
}
