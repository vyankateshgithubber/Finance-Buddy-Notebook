import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, Label } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent, ChartLegend, ChartLegendContent, type ChartConfig } from "@/components/ui/chart"

interface CategoryTotal {
    category: string;
    total: number;
    [key: string]: string | number;
}

// Define a palette of colors for dynamic categories
const CHART_COLORS = [
    "hsl(var(--chart-1))",
    "hsl(var(--chart-2))",
    "hsl(var(--chart-3))",
    "hsl(var(--chart-4))",
    "hsl(var(--chart-5))",
    "hsl(var(--chart-1))", // Repeat if necessary or add more
];

export function Dashboard({ refreshTrigger }: { refreshTrigger: number }) {
    const [data, setData] = useState<CategoryTotal[]>([]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await api.get('/insights');
                setData(res.data);
            } catch (error) {
                console.error("Error fetching insights:", error);
            }
        };
        fetchData();
    }, [refreshTrigger]);

    const totalSpent = useMemo(() => {
        return data.reduce((acc, curr) => acc + curr.total, 0);
    }, [data]);

    // Dynamically generate chart config based on data
    const chartConfig = useMemo(() => {
        const config: ChartConfig = {
            total: {
                label: "Total Spent",
                color: "hsl(var(--chart-1))",
            },
        };
        data.forEach((item, index) => {
            config[item.category] = {
                label: item.category,
                color: CHART_COLORS[index % CHART_COLORS.length],
            };
        });
        return config;
    }, [data]);

    return (
        <Card className="flex flex-col h-full shadow-md border-0 bg-card/50">
            <CardHeader className="items-center pb-0">
                <CardTitle>Spending by Category</CardTitle>
                <CardDescription>Current Month</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 pb-0">
                {data.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                        No data available
                    </div>
                ) : (
                    <ChartContainer
                        config={chartConfig}
                        className="mx-auto aspect-square max-h-[300px]"
                    >
                        <PieChart>
                            <ChartTooltip
                                cursor={false}
                                content={<ChartTooltipContent hideLabel />}
                            />
                            <Pie
                                data={data}
                                dataKey="total"
                                nameKey="category"
                                innerRadius={60}
                                strokeWidth={5}
                            >
                                <Label
                                    content={({ viewBox }) => {
                                        if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                                            return (
                                                <text
                                                    x={viewBox.cx}
                                                    y={viewBox.cy}
                                                    textAnchor="middle"
                                                    dominantBaseline="middle"
                                                >
                                                    <tspan
                                                        x={viewBox.cx}
                                                        y={viewBox.cy}
                                                        className="fill-foreground text-3xl font-bold"
                                                    >
                                                        ${totalSpent.toLocaleString()}
                                                    </tspan>
                                                    <tspan
                                                        x={viewBox.cx}
                                                        y={(viewBox.cy || 0) + 24}
                                                        className="fill-muted-foreground"
                                                    >
                                                        Total
                                                    </tspan>
                                                </text>
                                            )
                                        }
                                    }}
                                />
                            </Pie>
                            <ChartLegend content={<ChartLegendContent nameKey="category" />} className="-translate-y-2 flex-wrap gap-2 [&>*]:basis-1/4 [&>*]:justify-center" />
                        </PieChart>
                    </ChartContainer>
                )}
            </CardContent>
            <CardFooter className="flex-col gap-2 text-sm">
                <div className="leading-none text-muted-foreground">
                    Showing total spending for the current period
                </div>
            </CardFooter>
        </Card>
    );
}
