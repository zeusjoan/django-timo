const months = {
    1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień",
    5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień",
    9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"
};

const colors = {
    capex: '#8884d8',
    opex: '#82ca9d',
    consultation: '#ffc658'
};

document.addEventListener('DOMContentLoaded', function() {
    // Sprawdzamy czy istnieją dane do wykresów
    if (typeof chartData === 'undefined') return;

    const data = JSON.parse(chartData);
    
    // Wykres słupkowy
    const barChartData = Object.entries(data.monthly_data).map(([month, values]) => ({
        name: months[parseInt(month)],
        CAPEX: values.capex,
        OPEX: values.opex,
        Konsultacje: values.consultation
    }));

    // Wykres kołowy - podsumowanie roczne
    const pieChartData = [
        { name: 'CAPEX', value: data.yearly_summary.capex },
        { name: 'OPEX', value: data.yearly_summary.opex },
        { name: 'Konsultacje', value: data.yearly_summary.consultation }
    ];

    // Wykres kołowy - nadgodziny
    const overtimePieData = [
        { name: 'CAPEX', value: data.overtime_data.capex },
        { name: 'OPEX', value: data.overtime_data.opex }
    ];

    // Tworzenie wykresu słupkowego
    const barChart = Recharts.BarChart;
    const bar = Recharts.Bar;
    const xAxis = Recharts.XAxis;
    const yAxis = Recharts.YAxis;
    const cartesianGrid = Recharts.CartesianGrid;
    const tooltip = Recharts.Tooltip;
    const legend = Recharts.Legend;
    const pieChart = Recharts.PieChart;
    const pie = Recharts.Pie;
    const cell = Recharts.Cell;

    // Renderowanie wykresów
    if (document.getElementById('monthlyChart')) {
        const monthlyChartContainer = document.getElementById('monthlyChart');
        ReactDOM.createRoot(monthlyChartContainer).render(
            React.createElement(barChart, { width: 800, height: 300, data: barChartData },
                React.createElement(cartesianGrid, { strokeDasharray: "3 3" }),
                React.createElement(xAxis, { dataKey: "name" }),
                React.createElement(yAxis),
                React.createElement(tooltip),
                React.createElement(legend),
                React.createElement(bar, { dataKey: "CAPEX", fill: colors.capex }),
                React.createElement(bar, { dataKey: "OPEX", fill: colors.opex }),
                React.createElement(bar, { dataKey: "Konsultacje", fill: colors.consultation })
            )
        );
    }

    if (document.getElementById('yearlyChart')) {
        const yearlyChartContainer = document.getElementById('yearlyChart');
        ReactDOM.createRoot(yearlyChartContainer).render(
            React.createElement(pieChart, { width: 400, height: 300 },
                React.createElement(pie, {
                    data: pieChartData,
                    cx: "50%",
                    cy: "50%",
                    labelLine: false,
                    label: ({ name, value, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`,
                    outerRadius: 100,
                    fill: "#8884d8",
                    dataKey: "value"
                })
            )
        );
    }

    if (document.getElementById('overtimeChart')) {
        const overtimeChartContainer = document.getElementById('overtimeChart');
        ReactDOM.createRoot(overtimeChartContainer).render(
            React.createElement(pieChart, { width: 400, height: 300 },
                React.createElement(pie, {
                    data: overtimePieData,
                    cx: "50%",
                    cy: "50%",
                    labelLine: false,
                    label: ({ name, value, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`,
                    outerRadius: 100,
                    fill: "#8884d8",
                    dataKey: "value"
                })
            )
        );
    }
});