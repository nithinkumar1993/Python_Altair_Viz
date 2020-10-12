from flask import Flask, render_template, request, session, redirect
import more_itertools
import altair as alt
import pandas as pd


app = Flask(__name__)


tidy_df = pd.read_csv("data/tidy_esb.csv")  

Councils = sorted(tidy_df['County Councils'].unique())  # Unique list of Councils.
Years = sorted(tidy_df.Year.unique())   # Unique list of Years


tidy_df['date'] = pd.to_datetime(tidy_df['date'])
tidy_df.loc[tidy_df['date'].dt.month <= 6,'Half'] = 1
tidy_df.loc[tidy_df['date'].dt.month > 6,'Half'] = 2
    


def produce_table(item, size=10):

    if item == "Council":
        var = Councils
    else:
        var = Years

    output = "<table>"
    for chunk in more_itertools.chunked(var, size):
        output += "<tr>"
        for s in chunk:
            output += f"<td><input type='checkbox' name='{s}' value='{s}'>{s}</td>"
        output += "</tr>"
    output += "</table>"
    return output


@app.route("/")
@app.route("/councils")
def intro():
    return render_template("/intro.html")

@app.route("/county")
def show_symbols():
    the_table = produce_table("Council", 6)
    return render_template("county.html", data=the_table)


@app.route("/processchecks", methods=["POST"])
def process_checks():
    
    print(request.form)  # This gets at the FORM data.
    print(list(request.form.keys()))
    session["selection"] = list(request.form.keys())
   
    return redirect("/yearselection")

@app.route("/yearselection")
def show_years():
    year_table = produce_table("year", 1)
    return render_template("yearslist.html", data=year_table)

@app.route("/processyears", methods=["POST"])
def process_years():
    
    print(request.form)  # This gets at the FORM data.
    #print(list(request.form.keys()))
    session["year"] = list(request.form.keys())
   
    return redirect("/visual")

@app.route("/visual")
def display_the_visplot():

    # Dynamic graph for selected councils
    df_vis = pd.concat(
        tidy_df[tidy_df["County Councils"] == county] for county in session["selection"]
    )
    df = pd.concat(
        df_vis[df_vis["Year"] == int(row)] for row in session["year"]
    )

    l_plot = alt.Chart(df).mark_line().encode(
        x = alt.X('date',
            title="Year"),
        y = alt.Y('esb',
            title="ESB Count"),
        color = "County Councils"
        ).properties(
            title = "ESB connections distribution for selected data",
            width = 800).interactive()
    s_plot = alt.Chart(df).mark_circle(size=30).encode(
        x='date',
        y='esb',
        color=alt.value('black'),
        tooltip=["County Councils",'esb',"date"]
        ).interactive()
    
    plot = l_plot + s_plot

    plot.save("templates/visplot.html")

    return render_template("visplot.html")


@app.route("/barplot")
def display_the_barplot():

    bars = alt.Chart(tidy_df).mark_bar().encode(
        x=alt.X('sum(esb):Q', stack='zero'),
        y=alt.Y('County Councils:N'),
        color='County Councils'
        ).properties(
            title = "ESB connections for each County")

    text = alt.Chart(tidy_df).mark_text(dx=-25, dy=1.5, size = 12, color='white').encode(
       x=alt.X('sum(esb):Q', stack='zero'),
        y=alt.Y('County Councils:N'),
        detail='County Councils:N',
        text=alt.Text('sum(esb)', format='.1f')
        )

    barplot = bars + text
    barplot.save("templates/barplot.html")

    return render_template("barplot.html")

@app.route("/lineplot")
def display_the_lineplot():

    lineplot = alt.Chart(tidy_df).mark_line().encode(
        x = alt.X('date',
            title="Year"),
        y = alt.Y('esb',
            aggregate = "average",
            title="ESB Count"),
        color = alt.value('green')
        ).properties(
            title = "ESB connections Trend")
    
    lineplot.save("templates/lineplot.html")

    return render_template("lineplot.html")

@app.route("/facetplot")
def display_the_facetplot():

    facetplot = alt.Chart(tidy_df).mark_area().encode(
        x='Year:O',
        y=alt.Y(
            'sum(esb):Q',
            title='ESB Connections',
            axis=alt.Axis(format='~s')
        ),
        facet=alt.Facet('County Councils:O', columns=4),
        color = 'County Councils'
        ).properties(
            title='ESB Connections trend for each County',
        )
    
    facetplot.save("templates/facetplot.html")

    return render_template("facetplot.html")

@app.route("/boxplot")
def display_the_boxplot():

    boxplot = alt.Chart(tidy_df).mark_boxplot(size = 30).encode(
            x=alt.X('Year:O',
                    title = 'Years'),
            y=alt.Y('esb:Q',
                    title = 'ESB Count')
        ).properties(width=350,
        title = "Max,Min,all the Quartiles for each year")
    
    boxplot.save("templates/boxplot.html")

    return render_template("boxplot.html")

@app.route("/conplot")
def display_the_conplot():


    slider = alt.binding_range(min=2006, max=2013, step=1)
    select_year = alt.selection_single(name='Select', fields=['Year'],
                                    bind=slider, init={'Year': 2006})

    base = alt.Chart(tidy_df).add_selection(
            select_year
        ).transform_filter(
            select_year
        ).transform_calculate(
            types=alt.expr.if_(alt.datum.Half == 1.0, '1st Half', '2nd Half')
        ).properties(
            width=250,
        )

    color_scale = alt.Scale(domain=['1st Half', '2nd Half'],
                                range=['green', 'orange'])

    left = base.transform_filter(
            alt.datum.types == '1st Half'
        ).encode(
            y=alt.Y('County Councils:O', axis=None),
            x=alt.X('sum(esb):Q',
                    title='ESB Count',
                    sort=alt.SortOrder('descending')),
            color=alt.Color('types:N', scale=color_scale, legend=None),
            tooltip = ('sum(esb):Q')
        ).mark_bar().properties(title='First Half of Year')

    middle = base.encode(
            y=alt.Y('County Councils:O', axis=None),
            text=alt.Text('County Councils:O'),
        ).mark_text(color = 'steelblue',size = 15).properties(width=105)


    right = base.transform_filter(
            alt.datum.types == '2nd Half'
        ).encode(
            y=alt.Y('County Councils:O', axis=None),
            x=alt.X('sum(esb):Q', title='ESB Count'),
            color=alt.Color('types:N', scale=color_scale, legend=None),
            tooltip = ('sum(esb):Q')
        ).mark_bar().properties(title='Second Half of Year')

    conplot = alt.concat(left, middle, right, spacing=5)

    conplot.save("templates/conplot.html")

    return render_template("conplot.html")



app.secret_key = "fdhfsb/cv35/vsd@#/GV3hjH4b9.;bjhBDJHbjdhj6*"


if __name__ == "__main__":
    app.run(debug=True)
