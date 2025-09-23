import { Avatar, AvatarFallback } from '@/components/ui/avatar';

export default function SocialProof() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-16 pb-16">
      <div className="flex flex-col items-center text-center">
        <p className="text-sm text-muted-foreground mb-6">Trusted by music lovers</p>
        <div className="flex items-center space-x-4">
          <div className="flex -space-x-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <Avatar key={i} className="border-2 border-background">
                <AvatarFallback className="text-xs">U{i}</AvatarFallback>
              </Avatar>
            ))}
          </div>
          <div className="text-left">
            <p className="text-sm font-medium">1,000+ playlists created</p>
            <p className="text-xs text-muted-foreground">Join the community</p>
          </div>
        </div>
      </div>
    </div>
  );
}