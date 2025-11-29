"use client"

import * as React from "react"
import { Send, Plus, Split, BarChart3, Bot, User } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

interface Message {
    role: "user" | "assistant"
    content: string
}

export function Chat() {
    const [messages, setMessages] = React.useState<Message[]>([
        { role: "assistant", content: "Hello! I'm FrugalAgent. How can I help you manage your expenses today?" }
    ])
    const [input, setInput] = React.useState("")
    const [isLoading, setIsLoading] = React.useState(false)
    const scrollAreaRef = React.useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        if (scrollAreaRef.current) {
            const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollContainer) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        }
    }

    React.useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSend = async () => {
        if (!input.trim()) return

        const userMessage: Message = { role: "user", content: input }
        setMessages(prev => [...prev, userMessage])
        setInput("")
        setIsLoading(true)

        try {
            const response = await fetch("https://curly-waddle-p967j674vxwc6xr5-8000.app.github.dev/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: "1234", message: userMessage.content }),
            }).catch((error) => {
                console.error("Network error:", error)
                throw error
            });

            if (!response.ok) throw new Error("Failed to fetch response")

            const data = await response.json()
            const botMessage: Message = { role: "assistant", content: data.response }
            setMessages(prev => [...prev, botMessage])
        } catch (error) {
            console.error(error)
            setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error. Please try again." }])
        } finally {
            setIsLoading(false)
        }
    }

    const handleQuickAction = (action: string) => {
        let prompt = ""
        switch (action) {
            case "add":
                prompt = "I want to add an expense."
                break
            case "split":
                prompt = "I want to split an expense."
                break
            case "insights":
                prompt = "Show me my spending insights."
                break
        }
        setInput(prompt)
        // Optional: Auto-send or let user edit
    }

    return (
        <Card className="w-full max-w-2xl mx-auto h-[80vh] flex flex-col shadow-xl">
            <CardHeader className="border-b bg-muted/50">
                <CardTitle className="flex items-center gap-2">
                    <Bot className="w-6 h-6" />
                    FrugalAgent
                </CardTitle>
            </CardHeader>

            <CardContent className="flex-1 p-0 overflow-hidden">
                <ScrollArea className="h-full p-4" ref={scrollAreaRef}>
                    <div className="flex flex-col gap-4">
                        {messages.map((msg, index) => (
                            <div
                                key={index}
                                className={cn(
                                    "flex gap-3 max-w-[80%]",
                                    msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
                                )}
                            >
                                <Avatar className="w-8 h-8 border">
                                    {msg.role === "user" ? (
                                        <>
                                            <AvatarImage src="/user-avatar.png" />
                                            <AvatarFallback><User className="w-4 h-4" /></AvatarFallback>
                                        </>
                                    ) : (
                                        <>
                                            <AvatarImage src="/bot-avatar.png" />
                                            <AvatarFallback><Bot className="w-4 h-4" /></AvatarFallback>
                                        </>
                                    )}
                                </Avatar>

                                <div
                                    className={cn(
                                        "rounded-lg p-3 text-sm",
                                        msg.role === "user"
                                            ? "bg-primary text-primary-foreground"
                                            : "bg-muted text-foreground"
                                    )}
                                >
                                    <div className="prose dark:prose-invert max-w-none text-sm break-words">
                                        <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            components={{
                                                p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />
                                            }}
                                        >
                                            {msg.content}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="flex gap-3 mr-auto max-w-[80%]">
                                <Avatar className="w-8 h-8 border">
                                    <AvatarFallback><Bot className="w-4 h-4" /></AvatarFallback>
                                </Avatar>
                                <div className="bg-muted rounded-lg p-3 text-sm flex items-center gap-1">
                                    <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                                    <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                                    <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                                </div>
                            </div>
                        )}
                    </div>
                </ScrollArea>
            </CardContent>

            <CardFooter className="border-t bg-muted/50 p-4 flex flex-col gap-3">
                {/* Quick Actions */}
                <div className="flex gap-2 w-full overflow-x-auto pb-2">
                    <Button variant="outline" size="sm" onClick={() => handleQuickAction("add")} className="gap-2">
                        <Plus className="w-4 h-4" /> Add Expense
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleQuickAction("split")} className="gap-2">
                        <Split className="w-4 h-4" /> Split Bill
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => handleQuickAction("insights")} className="gap-2">
                        <BarChart3 className="w-4 h-4" /> Insights
                    </Button>
                </div>

                {/* Input Area */}
                <form
                    onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                    className="flex w-full gap-2"
                >
                    <Input
                        placeholder="Type a message..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={isLoading}
                        className="flex-1"
                    />
                    <Button type="submit" disabled={isLoading || !input.trim()}>
                        <Send className="w-4 h-4" />
                        <span className="sr-only">Send</span>
                    </Button>
                </form>
            </CardFooter>
        </Card>
    )
}
