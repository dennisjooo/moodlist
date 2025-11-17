'use client';

import { ProgressTimeline, StatusMessage } from '@/components/features/create/session/SessionProgressCard';

interface StatusSectionProps {
	status: string | null;
	currentStep: string;
}

export function StatusSection({ status, currentStep }: StatusSectionProps) {
	return (
		<div className="space-y-3">
			<StatusMessage
				status={status}
				currentStep={currentStep}
			/>
			<ProgressTimeline status={status} />
		</div>
	);
}
