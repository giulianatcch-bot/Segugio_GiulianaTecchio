import json
import chainlit as cl
from openai import OpenAI
from config import Config
from tavily import TavilyClient
from prompts import query_writer_instructions, summarizer_instructions, reflection_instruction

client = OpenAI(base_url=Config.AI_API_URL, api_key=Config.AI_API_KEY)

def llm(system_prompt, user_prompt, temperature=0):
    # HO RIMOSSO response_format per fare un test di sicurezza
    response = client.chat.completions.create(
        model=Config.LLM_MODEL_LOW,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature
    )
    return response.choices[0].message.content

def optimize_search_query(research_topic):
    formatted_instructions = query_writer_instructions.format(research_topic = research_topic)
    result = llm(formatted_instructions, "Genera una query per la ricerca web:")
    obj = json.loads(result)
    return obj

def _format_content(result):
    return f"""
    Fonte: {result['title']}:\n===\n
    URL: {result['url']}\n===\n
    Contenuto più rilevante: {result['content']}\n===\n
    """


def web_research(search_query):
    tavily_api_key="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"
    max_results = 10
    include_raw = False

    client = TavilyClient(api_key = tavily_api_key)
    response = client.search(
        query=search_query,
        max_results=max_results,
        include_raw_content=include_raw
    )
    results = response.get('results',[])
    titles = [result['title'] for result in results ]
    contents = [_format_content(result) for result in results]

    return {
        "sources_gathered": titles,
        "web_research_results": contents
    }
    
def summarize_sources(web_research_results, research_topic, running_summary=None):
        current_results = "\n".join(web_research_results)

        if running_summary:
            message = (
                f"Estendiquesto riassunto: {running_summary}\n\n"
                f"Con questi nuovi risultati: {current_results}"
                f"Sul tema: {research_topic}"
            )
        else:
            message = (
                f"Genera un riassunto di questi risultati: {current_results}"
                f"Sul Tema: {research_topic}"
            )

        output_formatter = None
        return llm(summarizer_instructions,message, 0.2)
    
def reflect_on_summary(research_topic, running_summary):
     result = llm(
          reflection_instruction.format(research_topic=research_topic),
          f"Identifica una lacuna e genera una domanda per la prossima ricerca basandoti su: {running_summary}"
     )

     return json.loads(result)

@cl.on_message
async def main(message: cl.Message):
    user_message = message.content
    osq = optimize_search_query(user_message)

    query, aspect, reason = osq['query'], osq['aspect'], osq['reason']
    await cl.Message(author="system_assistant", content=f"Query di ricerca ottimizzata:\n {query}. \n Mi sono soffermato su questo aspetto:\n {aspect}.\n Per questo motivo: \n {reason}.\n"
    ).send()

    running_summary =  None
    max_cycles = 4

    while True:
         
        results = web_research(query)
        titles ="\n".join(results['sources_gathered'])
        

        await cl.Message(author="system_assistant",
                     content=f"Fonti trovate: {titles}"
                     ).send()
        summary = summarize_sources(results['web_research_results'], query, running_summary)
        running_summary = summary

    
        await cl.Message(author="system_assistant", content=f"Riassunto attuale: {summary}").send()

        max_cycles -= 1
        if max_cycles <= 0:
             break
            

        ros = reflect_on_summary(query, summary)
   
        query = ros.get('domanda_approfondimento', f"Dimmi di più su {query}")
        lacuna_conoscenza = ros.get('lacuna_conoscenza', "")

        await cl.Message(
        author="system_assistant",
        content=f"Prossima ricerca:\n {query}.\n Mi sono soffermato su questo perchè':n{lacuna_conoscenza}"
                     ).send()
        
        await cl.Message(
        author="segugio_assistant",
        content=f"Risposta alla tua domanda:\n\n{message.content}\n\nRisposta finale:\n\n{running_summary}"
                     ).send()
