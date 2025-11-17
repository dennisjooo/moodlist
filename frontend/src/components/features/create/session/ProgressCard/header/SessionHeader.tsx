'use client';

import { Button } from '@/components/ui/button';
import { CardTitle } from '@/components/ui/card';
import { StatusIcon } from './StatusIcon';
import { UpdatePulse } from './UpdatePulse';

interface SessionHeaderProps {
	status: string | null;
	isActive: boolean;
	isCancelling: boolean;
	triggerKey: string;
	onCancelClick?: () => void;
}

export function SessionHeader({
	status,
	isActive,
	isCancelling,
	triggerKey,
	onCancelClick,
}: SessionHeaderProps) {
	return (
		<div className="flex items-center justify-between gap-3">
			<CardTitle className="text-base flex items-center gap-2.5 font-semibold">
				<StatusIcon status={status} />
				<span className="bg-gradient-to-br from-foreground to-foreground/80 bg-clip-text">
					{isCancelling ? 'Cancelling...' : 'Playlist Generation'}
				</span>
				{isActive && (
					<UpdatePulse
						triggerKey={triggerKey}
						className="ml-0.5"
					/>
				)}
			</CardTitle>
			{isActive && !isCancelling && (
				<Button
					variant="outline"
					size="sm"
					onClick={onCancelClick}
					className="hover:bg-destructive/10 hover:text-destructive hover:border-destructive/50 transition-colors"
				>
					Cancel
				</Button>
			)}
		</div>
	);
}
