import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface CancelWorkflowDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: () => void;
    isCancelling: boolean;
}

export function CancelWorkflowDialog({
    open,
    onOpenChange,
    onConfirm,
    isCancelling
}: CancelWorkflowDialogProps) {
    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Cancel Playlist Creation?</AlertDialogTitle>
                    <AlertDialogDescription>
                        Are you sure you want to cancel this workflow? Your progress will be lost and you'll need to start over.
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel disabled={isCancelling}>Keep Working</AlertDialogCancel>
                    <AlertDialogAction
                        onClick={onConfirm}
                        disabled={isCancelling}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                        {isCancelling ? 'Cancelling...' : 'Cancel Workflow'}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
