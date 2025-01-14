import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Download } from "lucide-react"
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

    const handleDownload = () => {
        const content = props.segments
            .map(segment => `[${formatTimestamp(segment.start)}] ${segment.text}`)
            .join('\n');

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // Remove any existing extension and add .txt
        const baseFileName = props.name.replace(/\.[^/.]+$/, '');
        a.download = baseFileName + '.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <Card className="w-full h-full flex flex-col">
            <CardHeader className="pb-2 flex-shrink-0">
                <div className="flex justify-between items-center mb-2">
                    <audio
                        ref={audioRef}
                        controls
                        src={props.url}
                        className="w-full"
                    >
                        Your browser does not support the audio element.
                    </audio>
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={handleDownload}
                                    className="ml-2 flex-shrink-0"
                                >
                                    <Download className="h-4 w-4" />
                                </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                                <p>Download the transcript</p>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </div>
            </CardHeader>
            <CardContent className="flex-1 p-0">
                <ScrollArea className="h-full w-full rounded-md border p-4">
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
