'use client';

import { ProgressTimeline } from './ProgressTimeline';
import { StatusMessage } from './StatusMessage';

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
