import { DossierLive } from "./DossierLive";

export default async function DossierPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DossierLive id={id} />;
}
