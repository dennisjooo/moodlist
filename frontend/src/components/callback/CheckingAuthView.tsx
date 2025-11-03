import { CardHeader, CardDescription } from "@/components/ui/card";
import { CallbackLayout } from "./CallbackLayout";
import { CallbackCard } from "./CallbackCard";

export function CheckingAuthView() {
  return (
    <CallbackLayout>
      <CallbackCard animate={false}>
        <CardHeader className="flex flex-col items-center gap-5 text-center py-12">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <CardDescription className="text-base text-muted-foreground">
            Checking authentication...
          </CardDescription>
        </CardHeader>
      </CallbackCard>
    </CallbackLayout>
  );
}
