import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Download } from "lucide-react"
import { useRef, useState, useEffect } from "react"

export default function VideoWithTranscript() {
    const [videoId, setVideoId] = useState("");

    useEffect(() => {
        // Extract video ID from YouTube URL
        if (props.url) {
            const url = new URL(props.url);
            const id = url.searchParams.get('v') ||
                      props.url.split('youtu.be/')[1] ||
                      props.url.split('v/')[1] ||
                      props.url.split('embed/')[1];

            setVideoId(id);
        }
    }, [props.url]);

    const handleSegmentClick = (startTime) => {
        if (videoId) {
            const iframe = document.querySelector('iframe');
            if (iframe && iframe.contentWindow) {
                // YouTube Player API - seek to specific time
                iframe.contentWindow.postMessage(
                    JSON.stringify({
                        event: 'command',
                        func: 'seekTo',
                        args: [startTime, true]
                    }), '*'
                );

                // Also play the video
                iframe.contentWindow.postMessage(
                    JSON.stringify({
                        event: 'command',
                        func: 'playVideo',
                        args: []
                    }), '*'
                );
            }
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
                    <div className="w-full">
                        <div className="relative w-full" style={{ paddingBottom: '56.25%', height: 0 }}>
                            {videoId && (
                                <iframe
                                    src={`https://www.youtube.com/embed/${videoId}?enablejsapi=1`}
                                    className="absolute top-0 left-0 w-full h-full"
                                    title="YouTube video player"
                                    frameBorder="0"
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                    allowFullScreen
                                ></iframe>
                            )}
                        </div>
                    </div>
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
