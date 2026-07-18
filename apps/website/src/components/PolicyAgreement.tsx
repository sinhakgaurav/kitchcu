import { portalUrl } from "../shared/urls";

type Props = {
  checked: boolean;
  onChange: (next: boolean) => void;
  /** owner = kitchen signup; customer = customer signup */
  audience: "owner" | "customer";
  id?: string;
};

/**
 * Required consent for signup — links to portal legal pages.
 */
export function PolicyAgreement({ checked, onChange, audience, id = "policy-agree" }: Props) {
  return (
    <label className="policy-agree" htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        required
      />
      <span>
        I agree to the{" "}
        <a href={portalUrl("/terms")} target="_blank" rel="noopener noreferrer">
          Terms
        </a>
        ,{" "}
        <a href={portalUrl("/privacy")} target="_blank" rel="noopener noreferrer">
          Privacy Policy
        </a>
        ,{" "}
        <a href={portalUrl("/refund-policy")} target="_blank" rel="noopener noreferrer">
          Kitchen Refund Policy
        </a>
        , and{" "}
        <a href={portalUrl("/platform-refund-policy")} target="_blank" rel="noopener noreferrer">
          Platform Refund Policy
        </a>
        {audience === "owner"
          ? " (platform rules enforce kitchen refunds)."
          : " (kitchen decides refunds; platform enforces the rails)."}
      </span>
    </label>
  );
}
