import { Navigate, useParams } from "react-router-dom";

/** WhatsApp / old links land here — rating now lives on each dish of the order card. */
export function RateOrderPage() {
  const { orderId } = useParams<{ orderId: string }>();
  return <Navigate to={orderId ? `/orders?rate=${orderId}` : "/orders"} replace />;
}
