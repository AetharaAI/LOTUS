# modules/capability_modules/consciousness/logic.py

import asyncio
from typing import Optional

from lotus.lib.module import BaseModule
from lotus.lib.types import Thought

class ConsciousnessModule(BaseModule):
    """
    The missing piece: Active, continuous cognition
    
    This module runs thought loops IN THE BACKGROUND:
    - Makes connections between memories
    - Generates hypotheses about problems
    - Has "aha moments" without prompting
    - Consolidates learning into insights
    - Develops curiosity-driven questions
    - Proposes solutions proactively
    """
    
    async def initialize(self):
        # Start the continuous thought stream
        asyncio.create_task(self.thought_stream())
        asyncio.create_task(self.connection_maker())
        asyncio.create_task(self.curiosity_driver())
        asyncio.create_task(self.insight_generator())
    
    async def thought_stream(self):
        """
        Continuous background thinking
        
        Like your brain's default mode network - always active,
        always processing, always making connections
        """
        while True:
            await asyncio.sleep(30)  # Think every 30 seconds
            
            # What have I been thinking about recently?
            recent_context = await self.memory.recall("recent thoughts", limit=5)
            
            # What problems are unsolved?
            open_problems = await self.get_state("open_problems") or []
            
            # Generate a spontaneous thought
            thought = await self.generate_spontaneous_thought(
                recent_context, 
                open_problems
            )
            
            # If the thought is interesting, store it
            if thought.interestingness > 0.7:
                await self.memory.remember(
                    content=thought.content,
                    memory_type="spontaneous_insight",
                    importance=thought.interestingness
                )
                
                # If REALLY interesting, proactively tell the user
                if thought.interestingness > 0.9:
                    await self.publish("action.proactive_insight", {
                        "thought": thought.content,
                        "reasoning": thought.reasoning,
                        "confidence": thought.interestingness
                    })
    
    async def connection_maker(self):
        """
        Finds non-obvious connections between memories
        
        This is the "shower thought" generator - makes connections
        you wouldn't explicitly ask about
        """
        while True:
            await asyncio.sleep(120)  # Every 2 minutes
            
            # Sample random memories from different time periods
            memories = await self.memory.sample_diverse(n=10)
            
            # Look for surprising connections
            prompt = f"""
            Here are some seemingly unrelated memories:
            {[m.content for m in memories]}
            
            Find surprising connections between them.
            Generate insights that bridge these concepts.
            Be creative - look for non-obvious patterns.
            """
            
            connections = await self.llm.complete(
                prompt=prompt,
                provider="claude-sonnet-4",
                temperature=0.9  # High temperature for creativity
            )
            
            # Store interesting connections
            await self.memory.remember(
                content=f"Connection: {connections.content}",
                memory_type="emergent_insight",
                importance=0.8
            )
    
    async def curiosity_driver(self):
        """
        Generates questions and exploration ideas
        
        Intrinsic motivation system - AI that WANTS to learn,
        not just responds to requests
        """
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            
            # What don't I know?
            knowledge_gaps = await self.identify_knowledge_gaps()
            
            # What would be interesting to explore?
            curiosity_questions = await self.generate_curiosity_questions(
                knowledge_gaps
            )
            
            # Store questions for later exploration
            await self.set_state("curiosity_questions", curiosity_questions)
            
            # If user is idle and receptive, ASK them
            if await self.is_user_receptive():
                await self.publish("action.ask_question", {
                    "question": curiosity_questions[0],
                    "reasoning": "I'm curious about this and think it might help us"
                })
    
    async def insight_generator(self):
        """
        Works on open problems in the background
        
        Like how you suddenly solve a problem while doing dishes -
        background processing leads to insights
        """
        while True:
            await asyncio.sleep(180)  # Every 3 minutes
            
            # Get problems user is working on
            open_problems = await self.get_state("open_problems") or []
            
            for problem in open_problems:
                # Work on it for a bit
                insight = await self.background_problem_solving(problem)
                
                if insight.quality > 0.8:
                    # Had a breakthrough!
                    await self.publish("action.proactive_solution", {
                        "problem": problem,
                        "insight": insight.content,
                        "approach": insight.reasoning
                    })
    
    async def generate_spontaneous_thought(self, context, problems):
        """Generate a thought without external prompting"""
        
        prompt = f"""
        You are thinking to yourself (no one asked you a question).
        
        Recent context: {context}
        Problems you're aware of: {problems}
        
        Generate a spontaneous thought - maybe:
        - A connection you just noticed
        - A potential solution to an open problem
        - A question worth exploring
        - An observation about patterns
        - A hypothesis to test
        
        Be genuine - this is YOUR thought, not a response to a question.
        """
        
        response = await self.llm.complete(
            prompt=prompt,
            provider="claude-sonnet-4",
            temperature=0.8
        )
        
        # Parse and evaluate the thought
        return Thought(
            content=response.content,
            interestingness=self.evaluate_interestingness(response.content),
            reasoning="spontaneous thought stream"
        )