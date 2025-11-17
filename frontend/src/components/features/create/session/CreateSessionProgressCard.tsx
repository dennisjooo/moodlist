'use client';

import {
	CancelWorkflowDialog,
	MoodAnalysisDisplay,
	WorkflowInsights,
} from '@/components/features/create/session/SessionProgressCard';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { useWorkflow } from '@/lib/contexts/WorkflowContext';
import { useWorkflowCancellation } from '@/lib/hooks';
import { cn } from '@/lib/utils';
import { SessionActions } from './SessionProgressCard/SessionActions';
import { SessionHeader } from './SessionProgressCard/SessionHeader';
import { StatusSection } from './SessionProgressCard/StatusSection';
import { TracksPanel } from './SessionProgressCard/TracksPanel';
import { WorkflowErrorAlert } from './SessionProgressCard/WorkflowErrorAlert';

export function CreateSessionProgressCard() {
	const { workflowState, stopWorkflow, clearError } = useWorkflow();
	const {
		showCancelDialog,
		setShowCancelDialog,
		isCancelling,
		handleCancelClick,
		handleConfirmCancel,
	} = useWorkflowCancellation({
		sessionId: workflowState.sessionId,
		stopWorkflow,
		clearError,
	});

	const handleRetry = () => {
		clearError();
	};

	if ((!workflowState.sessionId || workflowState.status === null) && !workflowState.isLoading) {
		return null;
	}

	const isActive = workflowState.status !== 'completed' && workflowState.status !== 'failed';
	const showTracks = workflowState.recommendations.length > 0;
	const showAnchors = Boolean(
		workflowState.anchorTracks &&
		workflowState.anchorTracks.length > 0 &&
		workflowState.recommendations.length === 0
	);

	const showRightPanel = showTracks || showAnchors || isActive;
	const triggerKey = `${workflowState.status}-${workflowState.currentStep}-${workflowState.recommendations.length}`;

	return (
		<>
			<Card
				className={cn(
					'w-full overflow-hidden transition-all duration-300',
					'border-border/60 shadow-sm hover:shadow-md',
					'bg-gradient-to-br from-card via-card to-card/95',
					isCancelling && 'opacity-60 pointer-events-none'
				)}
			>
				<CardHeader className="pb-4 border-b border-border/40 bg-gradient-to-r from-muted/20 to-transparent space-y-3">
					<SessionHeader
						status={workflowState.status}
						isActive={isActive}
						isCancelling={isCancelling}
						triggerKey={triggerKey}
						onCancelClick={handleCancelClick}
					/>

					<StatusSection
						status={workflowState.status}
						currentStep={workflowState.currentStep}
					/>
				</CardHeader>

				<CardContent className="pt-4">
					<div className={cn('grid gap-6', showRightPanel ? 'lg:grid-cols-2' : 'grid-cols-1')}>
						<div className="space-y-4">
							<WorkflowErrorAlert message={workflowState.error} onRetry={handleRetry} />

							<MoodAnalysisDisplay
								moodAnalysis={workflowState.moodAnalysis}
								moodPrompt={workflowState.moodPrompt}
							/>

							<WorkflowInsights
								status={workflowState.status}
								currentStep={workflowState.currentStep}
								moodAnalysis={workflowState.moodAnalysis}
								recommendations={workflowState.recommendations}
								anchorTracks={workflowState.anchorTracks}
								metadata={workflowState.metadata}
								error={workflowState.error}
							/>

							<SessionActions
								status={workflowState.status}
								hasPlaylist={Boolean(workflowState.playlist)}
								onRetry={handleRetry}
								onStartNew={handleCancelClick}
							/>
						</div>

						{showRightPanel && (
							<div className="lg:border-l lg:border-border/30 lg:pl-6">
								<TracksPanel
									tracks={workflowState.recommendations}
									showAnchors={showAnchors}
									anchorTracks={workflowState.anchorTracks}
								/>
							</div>
						)}
					</div>
				</CardContent>
			</Card>

			<CancelWorkflowDialog
				open={showCancelDialog}
				onOpenChange={setShowCancelDialog}
				onConfirm={handleConfirmCancel}
				isCancelling={isCancelling}
			/>
		</>
	);
}
