import { Card, CardHeader, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

export default function AudioWithTranscript() {
    return (
        <Card className="w-full max-w-3xl">
            <CardHeader className="pb-2">
                <audio
                    controls
                    src={props.audioUrl}
                    className="w-full"
                >
                    Your browser does not support the audio element.
                </audio>
            </CardHeader>
            <CardContent>
                <ScrollArea className="h-[300px] w-full rounded-md border p-4">
                    <p className="text-sm text-muted-foreground">
                        {props.transcript}
                    </p>
                </ScrollArea>
            </CardContent>
        </Card>
    )
}
