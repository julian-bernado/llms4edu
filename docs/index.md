---
layout: default
title: Leveraging LLMs for Data Analysis in Education Research
---

<header class="intro">
  <h1 id="presentation-title">Leveraging LLMs for Data Analysis<br>in Education Research</h1>
  <p><strong>{{ site.author }}</strong><br>{{ site.role }}<br>{{ site.affiliation }}</p>
  <p class="event-meta">
    {{ site.event_date }}<br>
    {{ site.event_time }}<br>
    {{ site.event_location }}
  </p>
</header>

<section class="resources" aria-labelledby="resources-heading">
  <h2 id="resources-heading">Workshop resources</h2>
  <ul>
    <li>
      <a href="{{ site.interactive_url }}">Interactive session</a>
    </li>
    <li>
      {% if site.slides_url and site.slides_url != "" %}
        <a href="{{ site.slides_url }}">Presentation slides</a>
      {% else %}
        Presentation slides <span class="note">(coming soon)</span>
      {% endif %}
    </li>
  </ul>
</section>

<footer>
  Stanford SCALE Initiative<br>
  Hosted on GitHub Pages · Made with Jekyll
</footer>
