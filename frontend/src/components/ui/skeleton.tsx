import { cn } from "@/lib/utils"

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
    shimmer?: boolean;
}

function Skeleton({
    className,
    shimmer = true,
    ...props
}: SkeletonProps) {
    return (
        <div
            className={cn(
                "relative overflow-hidden rounded-md",
                shimmer ? "animate-shimmer" : "animate-pulse bg-muted",
                className
            )}
            {...props}
        />
    )
}

export { Skeleton }
