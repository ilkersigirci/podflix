import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useRef } from "react"

export default function AudioWithTranscript() {
    const audioRef = useRef(null);

    const handleSegmentClick = (startTime) => {
        if (audioRef.current) {
            audioRef.current.currentTime = startTime;
            audioRef.current.play();
        }
    };

    const formatTimestamp = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <Card className="w-full max-w-3xl">
            <CardHeader className="pb-2">
                <audio
                    ref={audioRef}
                    controls
                    src={props.audioUrl}
                    className="w-full"
                >
                    Your browser does not support the audio element.
                </audio>
            </CardHeader>
            <CardContent>
                <ScrollArea className="h-[300px] w-full rounded-md border p-4">
                    <div className="space-y-2">
                        {props.segments.map((segment) => (
                            <div
                                key={segment.id}
                                onClick={() => handleSegmentClick(segment.start)}
                                className="flex gap-2 hover:bg-muted p-2 rounded-md cursor-pointer"
                            >
                                <span className="text-sm text-muted-foreground whitespace-nowrap">
                                    [{formatTimestamp(segment.start)}]
                                </span>
                                <p className="text-sm">
                                    {segment.text}
                                </p>
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    )
}
