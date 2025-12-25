import React, { useState, useRef, useEffect } from 'react';
import { api } from '@/lib/api';
import { Send, Bot, User } from 'lucide-react';
import { clsx } from 'clsx';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

interface Message {
    role: 'user' | 'bot';
    content: string;
}

export function ChatInterface({ onTransactionUpdate }: { onTransactionUpdate: () => void }) {
    const [messages, setMessages] = useState<Message[]>([
        { role: 'bot', content: 'Hello! I am your Frugal Agent. How can I help you manage your expenses today?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        if (scrollRef.current) {
            const scrollContainer = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollContainer) {
                scrollContainer.scrollTop = scrollContainer.scrollHeight;
            }
        }
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, loading]);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const res = await api.post('/chat', { message: userMsg });
            setMessages(prev => [...prev, { role: 'bot', content: res.data.response }]);
            onTransactionUpdate();
        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { role: 'bot', content: 'Sorry, I encountered an error processing your request.' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="h-full flex flex-col overflow-hidden border-0 shadow-lg">
            <CardHeader className="bg-primary text-primary-foreground py-4">
                <CardTitle className="flex items-center gap-2 text-lg">
                    <Bot size={24} />
                    Frugal Assistant
                </CardTitle>
            </CardHeader>

            <CardContent className="flex-1 p-0 overflow-hidden flex flex-col">
                <ScrollArea className="flex-1 p-4" ref={scrollRef}>
                    <div className="space-y-4 pr-4">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={clsx(
                                "flex gap-3 max-w-[85%]",
                                msg.role === 'user' ? "ml-auto flex-row-reverse" : "mr-auto"
                            )}>
                                <Avatar className="w-8 h-8">
                                    <AvatarFallback className={msg.role === 'user' ? "bg-primary text-primary-foreground" : "bg-green-600 text-white"}>
                                        {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                                    </AvatarFallback>
                                </Avatar>

                                <div className={clsx(
                                    "p-3 rounded-2xl text-sm shadow-sm",
                                    msg.role === 'user'
                                        ? "bg-primary text-primary-foreground rounded-tr-none"
                                        : "bg-muted text-foreground border rounded-tl-none"
                                )}>
                                    {msg.content}
                                </div>
                            </div>
                        ))}
                        {loading && (
                            <div className="flex gap-3 mr-auto">
                                <Avatar className="w-8 h-8">
                                    <AvatarFallback className="bg-green-600 text-white">
                                        <Bot size={16} />
                                    </AvatarFallback>
                                </Avatar>
                                <div className="bg-muted p-3 rounded-2xl rounded-tl-none border shadow-sm">
                                    <div className="flex gap-1">
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </ScrollArea>

                <div className="p-4 bg-background border-t">
                    <div className="flex gap-2">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                            placeholder="Type a message..."
                            disabled={loading}
                            className="flex-1"
                        />
                        <Button
                            onClick={sendMessage}
                            disabled={loading || !input.trim()}
                            size="icon"
                        >
                            <Send size={18} />
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}
